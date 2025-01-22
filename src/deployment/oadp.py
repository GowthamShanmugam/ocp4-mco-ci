import logging

from src.framework import config
from src.utility import constants
from src.utility.cmd import exec_cmd
from src.deployment.operator_deployment import OperatorDeployment
from src.utility.utils import get_non_acm_cluster_config


logger = logging.getLogger(__name__)


class OADPDeployment(OperatorDeployment):
    def __init__(self):
        super().__init__(constants.OADP_NAMESPACE, constants.OADP_OPERATOR_NAME)

    def do_deploy_oadp(self):
        """
        Deploy OADP Operator

        """
        if config.multicluster:
            managed_clusters = get_non_acm_cluster_config(include_acm=True)
            for cluster in managed_clusters:
                index = cluster.MULTICLUSTER["multicluster_index"]
                config.switch_ctx(index)
                logger.info(
                    f"Deploying OADP Operator for  cluster {cluster.ENV_DATA['cluster_name']}"
                )
                self.deploy_operator(
                    subscription_yaml=constants.OADP_SUBSCRIPTION_YAML,
                    ns_yaml=constants.OADP_NS_YAML,
                )
                logger.info("Creating Resource DataProtectionApplication")
                exec_cmd(f"oc apply -f {constants.DPA_DISCOVERED_APPS_PATH}")
            config.switch_default_cluster_ctx()
