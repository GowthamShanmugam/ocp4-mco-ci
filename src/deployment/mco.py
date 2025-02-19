import logging

from src.framework import config
from src.utility import constants, defaults
from src.ocs.resources.package_manifest import get_selector_for_ocs_operator
from src.deployment.operator_deployment import OperatorDeployment


logger = logging.getLogger(__name__)


class MCODeployment(OperatorDeployment):
    def __init__(self):
        super().__init__(
            config.ENV_DATA.get("mco_install_namespace")
            or constants.OPENSHIFT_OPERATORS,
            defaults.MCO_OPERATOR_NAME,
        )

    def deploy_prereq(self):
        # create MCO catalog source
        self.create_catalog_source()
        # enable odf-multicluster-console plugin
        self.enable_console_plugin(
            name=constants.MCO_PLUGIN_NAME,
            enable_console=config.MULTICLUSTER.get("enable_mco_plugin"),
        )
        # deploy MCO operator
        self.mco_subscription()

    def mco_subscription(self):
        logger.info("Deploying MCO operator.")
        operator_selector = get_selector_for_ocs_operator()
        custom_channel = config.DEPLOYMENT.get("ocs_csv_channel")
        self.deploy_operator(
            subscription_yaml=constants.SUBSCRIPTION_MCO_YAML,
            channel=custom_channel,
            operator_selector=operator_selector,
        )

    def create_config(self):
        pass

    @staticmethod
    def deploy_mco(log_cli_level="INFO"):
        pass
