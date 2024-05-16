"""
CatalogSource related functionalities
"""

import logging
from time import sleep

from src.utility.cmd import exec_cmd
from src.utility import constants
from src.ocs.ocp import OCP
from src.utility.exceptions import ResourceWrongStatusException, CommandFailed
from src.utility.retry import retry
from src.utility.timeout import TimeoutSampler
from src.utility.openshift_ops import OpenshiftOps

logger = logging.getLogger(__name__)


class CatalogSource(OCP):
    """
    This class represent CatalogSource and contains all related
    methods we need to do with it.
    """

    def __init__(
        self, resource_name="", namespace=None, cluster_kubeconfig="", *args, **kwargs
    ):
        """
        Initializer function for CatalogSource class
        Args:
            resource_name (str): Name of catalog source
            namespace (str): Namespace to which this catalogsource belongs
        """
        super(CatalogSource, self).__init__(
            resource_name=resource_name,
            namespace=namespace,
            kind="CatalogSource",
            cluster_kubeconfig=cluster_kubeconfig,
            *args,
            **kwargs,
        )

    @retry(ResourceWrongStatusException, tries=4, delay=5, backoff=1)
    def wait_for_state(self, state, timeout=480, sleep=5):
        """
        Wait till state of catalog source resource is the same as required one
        passed in the state parameter.
        Args:
            state (str): Desired state of catalog source object
            timeout (int): Timeout in seconds to wait for desired state
            sleep (int): Time in seconds to sleep between attempts
        Raises:
            ResourceWrongStatusException: In case the catalog source is not in
                expected state.
        """
        self.check_name_is_specified()
        sampler = TimeoutSampler(timeout, sleep, self.check_state, state=state)
        if not sampler.wait_for_func_status(True):
            raise ResourceWrongStatusException(
                f"Catalog source: {self.resource_name} is not in expected "
                f"state: {state}"
            )

    def check_state(self, state):
        """
        Check state of catalog source
        Args:
            state (str): State of CatalogSource object
        Returns:
            bool: True if state of object is the same as desired one, False
                otherwise.
        """
        self.check_name_is_specified()
        try:
            data = self.get()
        except CommandFailed:
            logger.info(f"Cannot find CatalogSource object {self.resource_name}")
            return False
        try:
            current_state = data["status"]["connectionState"]["lastObservedState"]
            logger.info(
                f"Catalog source {self.resource_name} is in state: " f"{current_state}!"
            )
            return current_state == state
        except KeyError:
            logger.info(
                f"Problem while reading state status of catalog source "
                f"{self.resource_name}, data: {data}"
            )
        return False


def disable_specific_source(source_name, cluster_kubeconfig=""):
    """
    Disable specific default source
    Args:
        source_name (str): Source name (e.g. redhat-operators)
    """
    logger.info(f"Disabling default source: {source_name}")
    OpenshiftOps.set_kubeconfig(cluster_kubeconfig)
    exec_cmd(
        constants.PATCH_SPECIFIC_SOURCES_CMD.format(
            disable="true", source_name=source_name
        )
    )
    logger.info(f"Waiting 20 seconds after disabling source: {source_name}")
    sleep(20)
