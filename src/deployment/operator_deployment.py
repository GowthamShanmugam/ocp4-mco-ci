import os
import logging
import tempfile
import time
import yaml

from src.framework import config
from src.utility.cmd import exec_cmd
from src.utility import constants, templating
from src.ocs.resources.catalog_source import disable_specific_source
from src.ocs.resources.catalog_source import CatalogSource
from src.utility.utils import (
    get_kube_config_path,
    create_directory_path,
    wait_for_machineconfigpool_status,
)
from src.utility.timeout import TimeoutSampler
from src.utility.exceptions import CommandFailed
from src.ocs import ocp
from src.ocs.resources.package_manifest import PackageManifest
from src.ocs.resources.csv import CSV

logger = logging.getLogger(__name__)


def get_and_apply_icsp_from_catalog(image, apply=True, insecure=False):
    """
    Get ICSP from catalog image (if exists) and apply it on the cluster (if
    requested).

    Args:
        image (str): catalog image of ocs registry.
        apply (bool): controls if the ICSP should be applied or not
            (default: true)
        insecure (bool): If True, it allows push and pull operations to registries to be made over HTTP

    Returns:
        str: path to the icsp.yaml file or empty string, if icsp not available
            in the catalog image

    """

    icsp_file_location = "/icsp.yaml"
    icsp_file_dest_dir = os.path.join(
        config.ENV_DATA["cluster_path"], f"icsp-{config.run_id}"
    )
    icsp_file_dest_location = os.path.join(icsp_file_dest_dir, "icsp.yaml")
    pull_secret_path = os.path.join(constants.TOP_DIR, "data", "pull-secret")
    create_directory_path(icsp_file_dest_dir)
    cmd = (
        f"oc image extract --filter-by-os linux/amd64 --registry-config {pull_secret_path} "
        f"{image} --confirm "
        f"--path {icsp_file_location}:{icsp_file_dest_dir}"
    )
    if insecure:
        cmd = f"{cmd} --insecure"
    exec_cmd(cmd)
    if not os.path.exists(icsp_file_dest_location):
        return ""

    # make icsp name unique - append run_id
    with open(icsp_file_dest_location) as f:
        icsp_content = yaml.safe_load(f)
    icsp_content["metadata"]["name"] += f"-{config.run_id}"
    with open(icsp_file_dest_location, "w") as f:
        yaml.dump(icsp_content, f)
    if apply:
        exec_cmd(f"oc apply -f {icsp_file_dest_location}")
        num_nodes = (
            config.ENV_DATA["worker_replicas"]
            + config.ENV_DATA["master_replicas"]
            + config.ENV_DATA.get("infra_replicas", 0)
        )
        timeout = 2800 if num_nodes > 6 else 1900
        wait_for_machineconfigpool_status(node_type="all", timeout=timeout)
    return icsp_file_dest_location


class OperatorDeployment(object):
    def __init__(self, namespace, name):
        self.namespace = namespace
        self.name = name

    def create_catalog_source(self, image=None):
        """
        This prepare catalog source manifest for deploy OCS operator from
        quay registry.
        Args:
            image (str): Image of ocs registry.
            ignore_upgrade (bool): Ignore upgrade parameter.
        """
        imagePath = image or config.ENV_DATA.get("ocs_registry_image", "")
        catalog_obj = CatalogSource(
            resource_name=constants.OPERATOR_CATALOG_SOURCE_NAME,
            namespace=constants.MARKETPLACE_NAMESPACE,
        ).get()
        # If the catalog already exists with the same image, skip creating it.
        if catalog_obj["spec"]["image"] == imagePath:
            return
        # Because custom catalog source will be called: redhat-operators, we need to disable
        # default sources. This should not be an issue as OCS internal registry images
        # are now based on OCP registry image
        disable_specific_source(
            constants.OPERATOR_CATALOG_SOURCE_NAME,
            get_kube_config_path(config.ENV_DATA["cluster_path"]),
        )
        logger.info("Adding CatalogSource")
        image_and_tag = imagePath.rsplit(":", 1)
        image = image_and_tag[0]
        image_tag = image_and_tag[1] if len(image_and_tag) == 2 else None
        catalog_source_data = templating.load_yaml(constants.CATALOG_SOURCE_YAML)
        cs_name = constants.OPERATOR_CATALOG_SOURCE_NAME
        change_cs_condition = (
            (image or image_tag)
            and catalog_source_data["kind"] == "CatalogSource"
            and catalog_source_data["metadata"]["name"] == cs_name
        )
        if change_cs_condition:
            default_image = config.ENV_DATA["default_ocs_registry_image"]
            image = image if image else default_image.rsplit(":", 1)[0]
            catalog_source_data["spec"][
                "image"
            ] = f"{image}:{image_tag if image_tag else 'latest'}"
        # apply icsp
        get_and_apply_icsp_from_catalog(image=imagePath, insecure=True)
        catalog_source_manifest = tempfile.NamedTemporaryFile(
            mode="w+", prefix="catalog_source_manifest", delete=False
        )
        templating.dump_data_to_temp_yaml(
            catalog_source_data, catalog_source_manifest.name
        )
        exec_cmd(f"oc apply -f {catalog_source_manifest.name}", timeout=2400)
        catalog_source = CatalogSource(
            resource_name=constants.OPERATOR_CATALOG_SOURCE_NAME,
            namespace=constants.MARKETPLACE_NAMESPACE,
        )
        # Wait for catalog source is ready
        catalog_source.wait_for_state("READY")

    def wait_for_subscription(self):
        """
        Wait for the subscription to appear
        Args:
            subscription_name (str): Subscription name pattern
        """

        resource_kind = constants.SUBSCRIPTION
        ocp.OCP(kind=resource_kind, namespace=self.namespace)
        for sample in TimeoutSampler(
            300, 10, ocp.OCP, kind=resource_kind, namespace=self.namespace
        ):
            subscriptions = sample.get().get("items", [])
            for subscription in subscriptions:
                found_subscription_name = subscription.get("metadata", {}).get(
                    "name", ""
                )
                if self.name in found_subscription_name:
                    logger.info(f"Subscription found: {found_subscription_name}")
                    return
                logger.debug(f"Still waiting for the subscription: {self.name}")

    def wait_for_csv(self):
        """
        Wait for th e CSV to appear
        Args:
            csv_name (str): CSV name pattern
        """
        ocp.OCP(kind="subscription", namespace=self.namespace)
        for sample in TimeoutSampler(
            300, 10, ocp.OCP, kind="csv", namespace=self.namespace
        ):
            csvs = sample.get().get("items", [])
            for csv in csvs:
                found_csv_name = csv.get("metadata", {}).get("name", "")
                if self.name in found_csv_name:
                    logger.info(f"CSV found: {found_csv_name}")
                    return
                logger.debug(f"Still waiting for the CSV: {self.name}")

    def enable_console_plugin(self, name, enable_console=True):
        """
        Enables console plugin for ODF
        """
        if enable_console:
            try:
                logger.info("Enabling console plugin")
                ocp_obj = ocp.OCP()
                patch = (
                    '\'[{"op": "add", "path": "/spec/plugins/-", "value": "$name"}]\''
                )
                patch = patch.replace("$name", name)
                patch_cmd = (
                    f"patch console.operator cluster -n {self.namespace}"
                    f" --type json -p {patch}"
                )
                ocp_obj.exec_oc_cmd(command=patch_cmd)
            except CommandFailed:
                patch = (
                    '\'[{"op": "add", "path": "/spec/plugins", "value": ["$name"]}]\''
                )
                patch = patch.replace("$name", name)
                patch_cmd = (
                    f"patch console.operator cluster -n {self.namespace}"
                    f" --type json -p {patch}"
                )
                ocp_obj.exec_oc_cmd(command=patch_cmd)
        else:
            logger.debug(f"Skipping console plugin for {name} operator ")

    def deploy_operator(
        self,
        subscription_yaml,
        ns_yaml=None,
        channel=None,
        operator_selector=None,
        sleep=120,
    ):
        """
        Deploy operator
        """
        logger.info("Creating Namespace")
        # creating Namespace and operator group for cert-manager
        logger.info("Creating namespace and operator group for Openshift-oadp")
        if ns_yaml:
            exec_cmd(f"oc apply -f {ns_yaml}")
        logger.info("Creating Operator Subscription")
        subscription_yaml_data = templating.load_yaml(subscription_yaml)
        package_manifest = PackageManifest(
            resource_name=self.name,
            selector=operator_selector,
        )
        # Wait for package manifest is ready
        package_manifest.wait_for_resource(timeout=300)
        default_channel = package_manifest.get_default_channel()
        subscription_yaml_data["spec"]["channel"] = (
            channel if channel else default_channel
        )
        subscription_yaml_data["spec"]["startingCSV"] = (
            package_manifest.get_current_csv(
                channel=channel if channel else default_channel
            )
        )
        subscription_manifest = tempfile.NamedTemporaryFile(
            mode="w+", prefix="subscription_manifest", delete=False
        )
        templating.dump_data_to_temp_yaml(
            subscription_yaml_data, subscription_manifest.name
        )
        exec_cmd(f"oc apply -f {subscription_manifest.name}")
        self.wait_for_subscription()
        logger.info(f"Sleeping for {sleep} seconds after subscribing Operator")
        time.sleep(sleep)
        subscriptions = ocp.OCP(
            kind=constants.SUBSCRIPTION_WITH_ACM,
            resource_name=self.name,
            namespace=self.namespace,
        ).get()
        csv_name = subscriptions["status"]["currentCSV"]
        csv = CSV(resource_name=csv_name, namespace=self.namespace)
        csv.wait_for_phase("Succeeded", timeout=720)
        logger.info("Operator Deployment Succeeded")
