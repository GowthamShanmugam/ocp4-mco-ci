import logging
import os
import base64
import tempfile
import time
from subprocess import PIPE, Popen

from src.framework import config
from src.ocs.resources.package_manifest import PackageManifest
from src.utility import constants, templating
from src.utility.utils import load_auth_config, clone_repo
from src.utility.cmd import exec_cmd
from src.utility.exceptions import CommandFailed
from src.ocs.resources.csv import CSV
from src.ocs.ocp import OCP
from src.deployment.operator_deployment import OperatorDeployment


logger = logging.getLogger(__name__)


class ACMDeployment(OperatorDeployment):
    def __init__(self):
        super().__init__(
            constants.ACM_OPERATOR_NAMESPACE, constants.ACM_HUB_OPERATOR_NAME
        )

    @staticmethod
    def validate_acm_hub_install():
        """
        Verify the ACM MultiClusterHub installation was successful.
        """
        logger.info("Verify ACM MultiClusterHub Installation")
        acm_mch = OCP(
            kind=constants.ACM_MULTICLUSTER_HUB,
            namespace=constants.ACM_HUB_NAMESPACE,
        )
        acm_mch.wait_for_resource(
            condition=constants.STATUS_RUNNING,
            resource_name=constants.ACM_MULTICLUSTER_RESOURCE,
            column="STATUS",
            timeout=720,
            sleep=5,
        )
        logger.info("MultiClusterHub Deployment Succeeded")

    def deploy_acm_hub_unreleased(self):
        """
        Handle ACM HUB unreleased image deployment
        """
        logger.info("Cloning open-cluster-management deploy repository")
        acm_hub_deploy_dir = os.path.join(
            constants.EXTERNAL_DIR, "acm_hub_unreleased_deploy"
        )
        clone_repo(constants.ACM_HUB_UNRELEASED_DEPLOY_REPO, acm_hub_deploy_dir)

        image_tag = config.MULTICLUSTER.get(
            "acm_unreleased_image",
            config.MULTICLUSTER.get("default_acm_unreleased_image"),
        )

        kubeconfig_location = os.path.join(
            config.ENV_DATA["cluster_path"], "auth", "kubeconfig"
        )

        logger.info("Setting env vars")
        env_vars = {}
        docker_config = load_auth_config().get("quay", {}).get("cli_password", {})
        if "DOWNSTREAM" in image_tag:
            logger.info("Retrieving quay token")
            pw = base64.b64decode(docker_config)
            pw = pw.decode().replace("quay.io", "quay.io:443").encode()
            quay_token = base64.b64encode(pw).decode()
            env_vars = {
                "QUAY_TOKEN": quay_token,
                "COMPOSITE_BUNDLE": "true",
                "CUSTOM_REGISTRY_REPO": "quay.io:443/acm-d",
                "DOWNSTREAM": "true",
                "DEBUG": "true",
                "KUBECONFIG": kubeconfig_location,
            }
        else:
            env_vars = {
                "QUAY_TOKEN": "",
                "COMPOSITE_BUNDLE": "true",
                "CUSTOM_REGISTRY_REPO": "quay.io/stolostron",
                "DOWNSTREAM": "false",
                "DEBUG": "true",
                "KUBECONFIG": kubeconfig_location,
            }
        for key, value in env_vars.items():
            if value:
                os.environ[key] = value

        logger.info("Writing pull-secret")
        _templating = templating.Templating(
            os.path.join(constants.TEMPLATE_DIR, "acm-deployment")
        )
        template_data = {"docker_config": docker_config}
        data = _templating.render_template(
            constants.ACM_HUB_UNRELEASED_PULL_SECRET_TEMPLATE,
            template_data,
        )
        pull_secret_path = os.path.join(
            acm_hub_deploy_dir, "prereqs", "pull-secret.yaml"
        )
        with open(pull_secret_path, "w") as f:
            f.write(data)

        logger.info("Creating ImageContentSourcePolicy")
        exec_cmd(f"oc apply -f {constants.ACM_HUB_UNRELEASED_ICSP_YAML}")

        logger.info("Writing tag data to snapshot.ver")
        with open(os.path.join(acm_hub_deploy_dir, "snapshot.ver"), "w") as f:
            f.write(image_tag)

        logger.info("Running open-cluster-management deploy")
        cmd = ["./start.sh", "--silent"]
        logger.info("Running cmd: %s", " ".join(cmd))
        proc = Popen(
            cmd,
            cwd=acm_hub_deploy_dir,
            stdout=PIPE,
            stderr=PIPE,
            encoding="utf-8",
        )
        stdout, stderr = proc.communicate()
        logger.info(stdout)
        if proc.returncode:
            logger.error(stderr)
            raise CommandFailed("open-cluster-management deploy script error")

        self.validate_acm_hub_install()

    def deploy_acm_hub_released(self):
        """
        Handle ACM HUB released image deployment
        """
        logger.info("Deploying ACM HUB Operator")
        channel = config.MULTICLUSTER.get("acm_hub_channel")
        self.deploy_operator(
            subscription_yaml=constants.ACM_HUB_SUBSCRIPTION_YAML,
            ns_yaml=constants.ACM_HUB_OPERATORGROUP_YAML,
            channel=channel,
        )
        logger.info("ACM HUB Operator Deployment Succeeded")

        logger.info("Creating MultiCluster Hub")
        exec_cmd(
            f"oc create -f {constants.ACM_HUB_MULTICLUSTERHUB_YAML} -n {constants.ACM_HUB_NAMESPACE}"
        )
        self.validate_acm_hub_install()
