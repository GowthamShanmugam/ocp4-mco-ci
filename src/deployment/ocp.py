import os
import logging
import json
import yaml

from src.utility import utils
from src.utility import constants
from src.exceptions.ocp_exceptions import PullSecretNotFoundException
from src.utility.defaults import (
    DEFAULT_PLATFORM,
    DEFAULT_CLUSTER_NAME,
    DEFAULT_CLUSTER_PATH,
)
from src.utility import templating

logger = logging.getLogger(__name__)

class OCPDeployment():
    def __init__(self, config):
        self.config = config

    def deploy_ocp(self, log_cli_level="DEBUG"):
        """
                Destroy OCP cluster specific
                Args:
                    log_level (str): log level openshift-installer (default: DEBUG)
        """
        if not self.config.ENV_DATA.get("skip_ocp_deployment", True):
            # download openshift installer
            installer_binary_path = self.download_installer()

            # create config
            cluster_install_path = self.create_config()

            # deploy cluster
            self.deploy(log_cli_level, installer_binary_path, cluster_install_path)


    def download_installer(self):
        return utils.download_installer(
            version=self.config.DEPLOYMENT["installer_version"],
            bin_dir=self.config.RUN["bin_dir"],
            force_download=self.config.DEPLOYMENT["force_download_installer"],
            config=self.config
        )

    def get_pull_secret(self):
        """
        Load pull secret file
        Returns:
            dict: content of pull secret
        """
        pull_secret_path = os.path.join(constants.TOP_DIR, "data", "pull-secret")
        is_exist = os.path.exists(pull_secret_path)
        if not is_exist:
            raise PullSecretNotFoundException(
                f"Pull secret does not exists on path: {pull_secret_path}."
            )
        with open(pull_secret_path, "r") as f:
            # Parse, then unparse, the JSON file.
            # We do this for two reasons: to ensure it is well-formatted, and
            # also to ensure it ends up as a single line.
            return json.dumps(json.loads(f.read()))

    def get_ssh_key(self):
        """
        Loads public ssh to be used for deployment
        Returns:
            str: public ssh key or empty string if not found
        """
        ssh_key = os.path.expanduser(self.config.DEPLOYMENT.get("ssh_key"))
        if not os.path.isfile(ssh_key):
            return ""
        with open(ssh_key, "r") as fs:
            lines = fs.readlines()
            return lines[0].rstrip("\n") if lines else ""

    def create_config(self):
        """
            Create the OCP deploy config
        """
        deployment_platform = self.config.ENV_DATA["platform"] or DEFAULT_PLATFORM
        cluster_name = self.config.ENV_DATA["cluster_name"] or DEFAULT_CLUSTER_NAME
        cluster_path = self.config.RUN["cluster_path"] or DEFAULT_CLUSTER_PATH
        cluster_install_path = os.path.join(cluster_path, cluster_name)
        # Generate install-config from template
        logger.info("Generating install-config")
        _templating = templating.Templating()
        ocp_install_template = (
            f"install-config-{deployment_platform.lower()}.yaml.j2"
        )
        ocp_install_template_path = os.path.join("ocp-deployment", ocp_install_template)
        install_config_str = _templating.render_template(
            ocp_install_template_path, self.config.ENV_DATA
        )
        # Log the install config *before* adding the pull secret,
        # so we don't leak sensitive data.
        logger.info(f"Install config: \n{install_config_str}")
        # Parse the rendered YAML so that we can manipulate the object directly
        install_config_obj = yaml.safe_load(install_config_str)
        install_config_obj["pullSecret"] = self.get_pull_secret()
        ssh_key = self.get_ssh_key()
        if ssh_key:
            install_config_obj["sshKey"] = ssh_key
        install_config_str = yaml.safe_dump(install_config_obj)
        install_config_path = os.path.join(cluster_install_path, "install-config.yaml")
        # create cluster directory
        os.mkdir(cluster_install_path)
        logger.info(f"Install directory: {cluster_install_path} is created successfully")
        with open(install_config_path, "w") as f:
            f.write(install_config_str)
        return cluster_install_path

    def deploy(self, log_cli_level="DEBUG", installer_binary_path="", cluster_install_path=""):
        utils.exec_cmd(
            cmd="{bin_dir} create cluster --dir {cluster_dir} --log-level={log_level}".format(
                bin_dir=installer_binary_path,
                cluster_dir=cluster_install_path,
                log_level=log_cli_level
            ),
            timeout=3600,
        )
