import logging
import tempfile
import time

from src.ocs import ocp
from src.ocs.resources.csv import CSV
from src.framework import config
from src.utility import constants, templating, defaults
from src.utility.cmd import exec_cmd
from src.ocs.resources.package_manifest import PackageManifest
from src.deployment.operator_deployment import OperatorDeployment
from src.utility.exceptions import UnexpectedDeploymentConfiguration

logger = logging.getLogger(__name__)


class GitopsDeployment(OperatorDeployment):
    def __init__(self):
        super().__init__(
            config.ENV_DATA.get("gitops_install_namespace")
            or constants.OPENSHIFT_OPERATORS
        )

    def deploy_prereq(self):
        # deploy GitOps operator
        self.gitops_subscription()

    def gitops_subscription(self):
        logger.info("Creating GitOps Operator Subscription")
        gitops_subscription_yaml_data = templating.load_yaml(
            constants.GITOPS_SUBSCRIPTION_YAML
        )
        package_manifest = PackageManifest(
            resource_name=constants.GITOPS_OPERATOR_NAME,
        )
        gitops_subscription_yaml_data["spec"]["startingCSV"] = (
            package_manifest.get_current_csv(
                channel="latest", csv_pattern=constants.GITOPS_OPERATOR_NAME
            )
        )
        gitops_subscription_manifest = tempfile.NamedTemporaryFile(
            mode="w+", prefix="gitops_subscription_manifest", delete=False
        )
        templating.dump_data_to_temp_yaml(
            gitops_subscription_yaml_data, gitops_subscription_manifest.name
        )
        exec_cmd(f"oc apply -f {gitops_subscription_manifest.name}")
        self.wait_for_subscription(constants.GITOPS_OPERATOR_NAME)
        logger.info("Sleeping for 90 seconds after subscribing to GitOps Operator")
        time.sleep(90)
        subscriptions = ocp.OCP(
            kind=constants.SUBSCRIPTION_WITH_ACM,
            resource_name=constants.GITOPS_OPERATOR_NAME,
            namespace=constants.OPENSHIFT_OPERATORS,
        ).get()
        gitops_csv_name = subscriptions["status"]["currentCSV"]
        csv = CSV(resource_name=gitops_csv_name, namespace=constants.GITOPS_NAMESPACE)
        csv.wait_for_phase("Succeeded", timeout=720)
        logger.info("GitOps Operator Deployment Succeeded")

    @staticmethod
    def deploy_gitops(log_cli_level="INFO"):
        logger.info("Creating GitOps CLuster Resource")
        exec_cmd(f"oc apply -f {constants.GITOPS_CLUSTER_YAML}")

        logger.info("Creating GitOps CLuster Placement Resource")
        exec_cmd(f"oc apply -f {constants.GITOPS_PLACEMENT_YAML}")

        logger.info("Creating ManagedClusterSetBinding")

        cluster_set = []
        managed_clusters = (
            ocp.OCP(kind=constants.ACM_MANAGEDCLUSTER).get().get("items", [])
        )
        # ignore local-cluster here
        for i in managed_clusters:
            if (
                i["metadata"]["name"] != constants.ACM_LOCAL_CLUSTER
                or config.MULTICLUSTER["primary_cluster"]
            ):
                cluster_set.append(
                    i["metadata"]["labels"][constants.ACM_CLUSTERSET_LABEL]
                )
        if all(x == cluster_set[0] for x in cluster_set):
            logger.info(f"Found the uniq clusterset {cluster_set[0]}")
        else:
            raise UnexpectedDeploymentConfiguration(
                "There are more then one clusterset added to multiple managedcluters"
            )

        managedclustersetbinding_obj = templating.load_yaml(
            constants.GITOPS_MANAGEDCLUSTER_SETBINDING_YAML
        )
        managedclustersetbinding_obj["metadata"]["name"] = cluster_set[0]
        managedclustersetbinding_obj["spec"]["clusterSet"] = cluster_set[0]
        managedclustersetbinding = tempfile.NamedTemporaryFile(
            mode="w+", prefix="managedcluster_setbinding", delete=False
        )
        templating.dump_data_to_temp_yaml(
            managedclustersetbinding_obj, managedclustersetbinding.name
        )
        exec_cmd(f"oc apply -f {managedclustersetbinding.name}")

        gitops_obj = ocp.OCP(
            resource_name=constants.GITOPS_CLUSTER_NAME,
            namespace=constants.GITOPS_CLUSTER_NAMESPACE,
            kind=constants.GITOPS_CLUSTER,
        )
        gitops_obj._has_phase = True
        gitops_obj.wait_for_phase("successful", timeout=720)
