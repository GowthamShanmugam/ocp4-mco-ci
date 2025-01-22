import logging

from src.ocs import ocp
from src.framework import config
from src.utility import constants, defaults
from src.utility.cmd import exec_cmd

from src.ocs.resources.package_manifest import get_selector_for_ocs_operator
from src.ocs.resources.stroage_cluster import StorageCluster
from src.deployment.operator_deployment import OperatorDeployment
from src.utility.exceptions import UnavailableResourceException, CommandFailed
from src.utility.retry import retry

logger = logging.getLogger(__name__)


class OCSDeployment(OperatorDeployment):
    def __init__(self):
        super().__init__(
            constants.OPENSHIFT_STORAGE_NAMESPACE, defaults.ODF_OPERATOR_NAME
        )

    def deploy_prereq(self):
        # create OCS catalog source
        self.create_catalog_source()
        # deploy ocs operator
        self.ocs_subscription()
        # enable odf-console plugin
        self.enable_console_plugin(
            constants.OCS_PLUGIN_NAME, config.ENV_DATA.get("enable_ocs_plugin")
        )
        # label nodes
        self.label_nodes()

    def ocs_subscription(self):
        logger.info("Deploying ODF operator.")
        exec_cmd(f"oc apply -f {constants.ODF_OLM_YAML}")
        operator_selector = get_selector_for_ocs_operator()
        custom_channel = config.DEPLOYMENT.get("ocs_csv_channel")
        self.deploy_operator(
            subscription_yaml=constants.SUBSCRIPTION_ODF_YAML,
            ns_yaml=constants.ODF_OLM_YAML,
            channel=custom_channel,
            operator_selector=operator_selector,
        )

    def label_nodes(self):
        nodes = ocp.OCP(kind="node").get().get("items", [])
        worker_nodes = [
            node
            for node in nodes
            if constants.WORKER_LABEL in node["metadata"]["labels"]
        ]
        if not worker_nodes:
            raise UnavailableResourceException("No worker node found!")
        az_worker_nodes = {}
        for node in worker_nodes:
            az = node["metadata"]["labels"].get(constants.ZONE_LABEL)
            az_node_list = az_worker_nodes.get(az, [])
            az_node_list.append(node["metadata"]["name"])
            az_worker_nodes[az] = az_node_list
        logger.debug(f"Found the worker nodes in AZ: {az_worker_nodes}")
        to_label = 3
        distributed_worker_nodes = []
        while az_worker_nodes:
            for az in list(az_worker_nodes.keys()):
                az_node_list = az_worker_nodes.get(az)
                if az_node_list:
                    node_name = az_node_list.pop(0)
                    distributed_worker_nodes.append(node_name)
                else:
                    del az_worker_nodes[az]
        logger.info(f"Distributed worker nodes for AZ: {distributed_worker_nodes}")
        distributed_worker_count = len(distributed_worker_nodes)
        if distributed_worker_count < to_label:
            logger.info(f"All nodes: {nodes}")
            logger.info(f"Distributed worker nodes: {distributed_worker_nodes}")
            raise UnavailableResourceException(
                f"Not enough distributed worker nodes: {distributed_worker_count} to label: "
            )
        _ocp = ocp.OCP(kind="node")
        workers_to_label = " ".join(distributed_worker_nodes[:to_label])
        if workers_to_label:
            logger.info(
                f"Label nodes: {workers_to_label} with label: "
                f"{constants.OPERATOR_NODE_LABEL}"
            )
            label_cmds = [
                (
                    f"label nodes {workers_to_label} "
                    f"{constants.OPERATOR_NODE_LABEL} --overwrite"
                )
            ]
            if config.DEPLOYMENT.get("infra_nodes") and not config.ENV_DATA.get(
                "infra_replicas"
            ):
                logger.info(
                    f"Label nodes: {workers_to_label} with label: "
                    f"{constants.INFRA_NODE_LABEL}"
                )
                label_cmds.append(
                    f"label nodes {workers_to_label} "
                    f"{constants.INFRA_NODE_LABEL} --overwrite"
                )

            for cmd in label_cmds:
                _ocp.exec_oc_cmd(command=cmd)

    @staticmethod
    def verify_storage_cluster(kubeconfig):
        """
        Verify storage cluster status
        """
        storage_cluster_name = constants.STORAGE_CLUSTER_NAME
        logger.info("Verifying status of storage cluster: %s", storage_cluster_name)
        storage_cluster = StorageCluster(
            resource_name=storage_cluster_name,
            namespace=constants.OPENSHIFT_STORAGE_NAMESPACE,
            cluster_kubeconfig=kubeconfig,
        )
        logger.info(
            f"Check if StorageCluster: {storage_cluster_name} is in Succeeded phase"
        )
        storage_cluster.wait_for_phase(phase="Ready", timeout=600)

    @retry(CommandFailed, tries=3, delay=30, backoff=1)
    @staticmethod
    def deploy_ocs_cluster(kubeconfig):
        _ocp = ocp.OCP(cluster_kubeconfig=kubeconfig)
        _ocp.exec_oc_cmd(f"apply -f {constants.STORAGE_CLUSTER_YAML}")

    @staticmethod
    def deploy_ocs(kubeconfig, skip_cluster_creation):
        # Do not access framework.config directly inside deploy_ocs, it is not thread safe
        if not skip_cluster_creation:
            OCSDeployment.deploy_ocs_cluster(kubeconfig)
            OCSDeployment.verify_storage_cluster(kubeconfig)
