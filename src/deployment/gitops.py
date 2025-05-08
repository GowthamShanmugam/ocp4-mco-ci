import logging
import tempfile

from src.ocs import ocp
from src.framework import config
from src.utility import constants, templating
from src.utility.cmd import exec_cmd
from src.deployment.operator_deployment import OperatorDeployment
from src.utility.exceptions import UnexpectedDeploymentConfiguration

logger = logging.getLogger(__name__)


class GitopsDeployment(OperatorDeployment):
    def __init__(self):
        super().__init__(
            config.ENV_DATA.get("gitops_install_namespace")
            or constants.OPENSHIFT_OPERATORS,
            constants.GITOPS_OPERATOR_NAME,
        )

    def deploy_prereq(self):
        # deploy GitOps operator
        self.gitops_subscription()

    def gitops_subscription(self):
        logger.info("Deploying GitOps operator.")
        self.deploy_operator(subscription_yaml=constants.GITOPS_SUBSCRIPTION_YAML)
    
    def gitops_role_binding(self):
        logger.info("Creating GitOps cluster role binding.")
        exec_cmd(f"oc apply -f {constants.GITOPS_ROLE_BINDING_YAML}")

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
