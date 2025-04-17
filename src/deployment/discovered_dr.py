import logging
import tempfile
import base64
import yaml

from src.framework import config
from src.deployment.oadp import OADPDeployment
from src.utility import constants
from src.utility import templating
from src.utility.utils import (
    get_non_acm_cluster_config,
    get_primary_cluster_config,
    exec_cmd,
)
from src.utility.version import (
    get_semantic_ocs_version_from_config,
    VERSION_4_19,
)
from src.ocs import ocp
from src.utility.exceptions import ResourceWrongStatusException, TimeoutExpiredError
from src.utility.timeout import TimeoutSampler

logger = logging.getLogger(__name__)


class DiscoveredDR(OADPDeployment):
    def __init__(self):
        super().__init__()

    def deploy(self):
        # deploy OADP operator
        self.do_deploy_oadp()

        # Configure mirror peer
        self._configure_mirror_peer()

        # Deploy dr policy
        self._deploy_dr_policy()

        # Add CaCert to Ramen hub ConfigMap
        self._add_cacert_ramen_configmap()

    def _configure_mirror_peer(self):
        config.switch_acm_ctx()
        # Create mirror peer
        odf_running_version = get_semantic_ocs_version_from_config()
        mirror_peer = constants.MIRROR_PEER_RDR_NEW
        if odf_running_version < VERSION_4_19:
            mirror_peer = constants.MIRROR_PEER_RDR_OLD
        mirror_peer_data = templating.load_yaml(mirror_peer)
        mirror_peer_yaml = tempfile.NamedTemporaryFile(
            mode="w+", prefix="mirror_peer", delete=False
        )
        # Update all the participating clusters in mirror_peer_yaml
        non_acm_clusters = get_non_acm_cluster_config(include_acm=True)
        primary = get_primary_cluster_config()
        non_acm_clusters.remove(primary)
        for cluster in non_acm_clusters:
            logger.info(f"{cluster.ENV_DATA['cluster_name']}")
        index = -1
        # First entry should be the primary cluster
        # in the mirror peer
        for cluster_entry in mirror_peer_data["spec"]["items"]:
            if index == -1:
                cluster_entry["clusterName"] = (
                    "local-cluster"
                    if primary.MULTICLUSTER["acm_cluster"]
                    else primary.ENV_DATA["cluster_name"]
                )
            else:
                cluster_entry["clusterName"] = non_acm_clusters[index].ENV_DATA[
                    "cluster_name"
                ]
            index += 1
        templating.dump_data_to_temp_yaml(mirror_peer_data, mirror_peer_yaml.name)
        exec_cmd(f"oc apply -f {mirror_peer_yaml.name}")
        self._validate_mirror_peer(mirror_peer_data["metadata"]["name"])
        config.switch_default_cluster_ctx()

    def _validate_mirror_peer(self, resource_name):
        """
        Validate mirror peer,
        Begins with CTX: ACM

        1. Check initial phase of 'ExchangingSecret'
        2. Check token-exchange-agent pod in 'Running' phase

        Raises:
            ResourceWrongStatusException: If pod is not in expected state

        """
        # Check mirror peer status only on HUB
        mirror_peer = ocp.OCP(
            kind="MirrorPeer",
            resource_name=resource_name,
        )
        mirror_peer._has_phase = True
        mirror_peer.get()
        try:
            mirror_peer.wait_for_phase(phase="ExchangedSecret", timeout=800)
            logger.info("Mirror peer is in expected phase 'ExchangedSecret'")
        except ResourceWrongStatusException:
            logger.exception("Mirror peer couldn't attain expected phase")
            raise

    def _deploy_dr_policy(self):
        """
        Deploy dr policy with MDR perspective, only on active ACM
        """
        config.switch_acm_ctx()
        # Create DR policy on ACM hub cluster
        dr_policy_hub_data = templating.load_yaml(constants.DR_POLICY_ACM_HUB)

        primary = get_primary_cluster_config()

        # Update DR cluster name and s3profile name
        dr_policy_hub_data["spec"]["drClusters"][0] = (
            "local-cluster"
            if primary.MULTICLUSTER["acm_cluster"]
            else primary.ENV_DATA["cluster_name"]
        )
        # Fill in for the rest of the non-acm clusters
        # index 0 is filled by primary
        index = 1
        for cluster in get_non_acm_cluster_config(include_acm=True):
            if cluster.ENV_DATA["cluster_name"] == primary.ENV_DATA["cluster_name"]:
                continue
            dr_policy_hub_data["spec"]["drClusters"][index] = cluster.ENV_DATA[
                "cluster_name"
            ]

        dr_policy_hub_yaml = tempfile.NamedTemporaryFile(
            mode="w+", prefix="dr_policy_hub_", delete=False
        )
        templating.dump_data_to_temp_yaml(dr_policy_hub_data, dr_policy_hub_yaml.name)
        self.dr_policy_name = dr_policy_hub_data["metadata"]["name"]
        exec_cmd(f"oc apply -f {dr_policy_hub_yaml.name}")
        # Check the status of DRPolicy and wait for 'Reason' field to be set to 'Succeeded'
        dr_policy_resource = ocp.OCP(
            kind="DRPolicy",
            resource_name=self.dr_policy_name,
        )
        dr_policy_resource.get()
        sample = TimeoutSampler(
            timeout=180,
            sleep=3,
            func=self._get_status,
            resource_data=dr_policy_resource,
        )
        if not sample.wait_for_func_status(True):
            raise TimeoutExpiredError("DR Policy failed to reach Succeeded state")
        config.switch_default_cluster_ctx()

    def _get_status(self, resource_data):
        resource_data.reload_data()
        reason = resource_data.data.get("status").get("conditions")[0].get("reason")
        if reason == "Succeeded":
            return True
        return False

    def _get_root_ca_cert(self):
        """
        Get root CA certificate
        """
        root_ca_cert = exec_cmd(
            "oc get cm user-ca-bundle -n openshift-config -o jsonpath=\"{['data']['ca-bundle\.crt']}\""
        )
        logger.info("Encoding Ca Cert")
        return base64.b64encode(root_ca_cert.stdout).decode("ascii")

    def _add_cacert_ramen_configmap(self):
        """
        Add CaCert to Ramen hub ConfigMap

        """
        config.switch_acm_ctx()
        ca_cert_data_encode = self._get_root_ca_cert()
        dr_ramen_hub_configmap_data = self._get_ramen_resource()
        ramen_config = yaml.safe_load(
            dr_ramen_hub_configmap_data.data["data"][
                constants.DR_RAMEN_CONFIG_MANAGER_KEY
            ]
        )
        logger.info("Adding Encoded Ca Cert to Ramen Hub configmap")
        for s3profile in ramen_config["s3StoreProfiles"]:
            s3profile["caCertificates"] = ca_cert_data_encode

        dr_ramen_hub_configmap_data_get = dr_ramen_hub_configmap_data.get()
        dr_ramen_hub_configmap_data_get["data"][
            constants.DR_RAMEN_CONFIG_MANAGER_KEY
        ] = str(ramen_config)
        logger.info("Applying changes to Ramen Hub configmap")
        self._update_config_map_commit(dict(dr_ramen_hub_configmap_data_get))
        config.switch_default_cluster_ctx()

    def _get_ramen_resource(self):
        dr_ramen_hub_configmap_data = ocp.OCP(
            kind="ConfigMap",
            resource_name=constants.DR_RAMEN_HUB_OPERATOR_CONFIG,
            namespace=constants.OPENSHIFT_OPERATORS,
        )
        dr_ramen_hub_configmap_data.get()
        return dr_ramen_hub_configmap_data

    def _update_config_map_commit(self, config_map_data, prefix=None):
        """
        merge the config and update the resource

        Args:
            config_map_data (dict): base dictionary which will be later converted to yaml content
            prefix (str): Used to identify temp yaml

        """
        logger.debug(
            "Converting Ramen section (which is string) to dict and updating "
            "config_map_data with the same dict"
        )
        ramen_section = {
            f"{constants.DR_RAMEN_CONFIG_MANAGER_KEY}": yaml.safe_load(
                config_map_data["data"].pop(f"{constants.DR_RAMEN_CONFIG_MANAGER_KEY}")
            )
        }
        logger.debug("Merge back the ramen_section with config_map_data")
        config_map_data["data"].update(ramen_section)
        for key in ["annotations", "creationTimestamp", "resourceVersion", "uid"]:
            if config_map_data["metadata"].get(key):
                config_map_data["metadata"].pop(key)

        dr_ramen_configmap_yaml = tempfile.NamedTemporaryFile(
            mode="w+", prefix=prefix, delete=False
        )
        yaml_serialized = yaml.dump(config_map_data)
        logger.debug(
            "Update yaml stream with a '|' for literal interpretation"
            " which comes exactly right after the key 'ramen_manager_config.yaml'"
        )
        yaml_serialized = yaml_serialized.replace(
            f"{constants.DR_RAMEN_CONFIG_MANAGER_KEY}:",
            f"{constants.DR_RAMEN_CONFIG_MANAGER_KEY}: |",
        )
        logger.info(f"after serialize {yaml_serialized}")
        dr_ramen_configmap_yaml.write(yaml_serialized)
        dr_ramen_configmap_yaml.flush()
        exec_cmd(f"oc apply -f {dr_ramen_configmap_yaml.name}")
