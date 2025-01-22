import logging
import os
import yaml
import time
import shlex
import re

from src.utility.retry import retry
from src.utility.timeout import TimeoutSampler
from src.framework import config
from src.utility.exceptions import (
    ResourceNameNotSpecifiedException,
    ResourceWrongStatusException,
    CommandFailed,
    TimeoutExpiredError,
    NotSupportedFunctionError,
)
from src.utility.cmd import exec_cmd

log = logging.getLogger(__name__)


class OCP(object):
    """
    A basic OCP object to run basic 'oc' commands
    """

    _has_phase = False

    def __init__(
        self,
        api_version="v1",
        kind="Service",
        namespace=None,
        resource_name="",
        selector=None,
        field_selector=None,
        cluster_kubeconfig="",
        threading_lock=None,
        silent=False,
        skip_tls_verify=False,
    ):
        """
        Initializer function
        Args:
            api_version (str): TBD
            kind (str): TBD
            namespace (str): The name of the namespace to use
            resource_name (str): Resource name
            selector (str): The label selector to look for. It has higher
                priority than resource_name and is used instead of the name.
            field_selector (str): Selector (field query) to filter on, supports
                '=', '==', and '!='. (e.g. status.phase=Running)
            cluster_kubeconfig (str): Path to the cluster kubeconfig file. Useful in a multicluster configuration
            threading_lock (threading.Lock): threading.Lock object that is used
                for handling concurrent oc commands
            silent (bool): If True will silent errors from the server, default false
            skip_tls_verify (bool): Adding '--insecure-skip-tls-verify' to oc command for
                exec_oc_cmd
        """
        self._api_version = api_version
        self._kind = kind
        self._namespace = namespace
        self._resource_name = resource_name
        self._data = {}
        self.selector = selector
        self.field_selector = field_selector
        self.cluster_kubeconfig = cluster_kubeconfig
        self.threading_lock = threading_lock
        self.silent = silent
        self.skip_tls_verify = skip_tls_verify

    @property
    def api_version(self):
        return self._api_version

    @property
    def kind(self):
        return self._kind

    @property
    def namespace(self):
        return self._namespace

    @property
    def resource_name(self):
        return self._resource_name

    @property
    def data(self, silent=False):
        if self._data:
            return self._data
        if self.silent:
            silent = True
        self._data = self.get(silent=silent)
        return self._data

    def reload_data(self):
        """
        Reloading data of OCP object
        """
        self._data = self.get()

    def check_name_is_specified(self, resource_name=""):
        """
        Check if the name of the resource is specified in class level and
        if not raise the exception.
        Raises:
            ResourceNameNotSpecifiedException: in case the name is not
                specified.
        """
        resource_name = resource_name if resource_name else self.resource_name
        if not resource_name:
            raise ResourceNameNotSpecifiedException(
                "Resource name has to be specified in class!"
            )

    def get(
        self,
        resource_name="",
        out_yaml_format=True,
        selector=None,
        all_namespaces=False,
        retry=0,
        wait=3,
        dont_raise=False,
        silent=False,
        field_selector=None,
        skip_tls_verify=False,
    ):
        """
        Get command - 'oc get <resource>'
        Args:
            resource_name (str): The resource name to fetch
            out_yaml_format (bool): Adding '-o yaml' to oc command
            selector (str): The label selector to look for.
            all_namespaces (bool): Equal to oc get <resource> -A
            retry (int): Number of attempts to retry to get resource
            wait (int): Number of seconds to wait between attempts for retry
            dont_raise (bool): If True will raise when get is not found
            field_selector (str): Selector (field query) to filter on, supports
                '=', '==', and '!='. (e.g. status.phase=Running)
            skip_tls_verify (bool): Adding '--insecure-skip-tls-verify' to oc command
        Example:
            get('my-pv1')
        Returns:
            dict: Dictionary represents a returned yaml file
            None: Incase dont_raise is True and get is not found
        """
        resource_name = resource_name if resource_name else self.resource_name
        selector = selector if selector else self.selector
        field_selector = field_selector if field_selector else self.field_selector
        if selector or field_selector:
            resource_name = ""
        command = f"get {self.kind} {resource_name}"
        if all_namespaces and not self.namespace:
            command += " -A"
        elif self.namespace:
            command += f" -n {self.namespace}"
        if selector is not None:
            command += f" --selector={selector}"
        if field_selector is not None:
            command += f" --field-selector={field_selector}"
        if out_yaml_format:
            command += " -o yaml"
        retry += 1
        while retry:
            try:
                return self.exec_oc_cmd(
                    command,
                    silent=silent,
                    skip_tls_verify=skip_tls_verify,
                )
            except CommandFailed as ex:
                if not silent:
                    log.warning(
                        f"Failed to get resource: {resource_name} of kind: "
                        f"{self.kind}, selector: {selector}, Error: {ex}"
                    )
                retry -= 1
                if not retry:
                    if not silent:
                        log.warning("Number of attempts to get resource reached!")
                    if not dont_raise:
                        raise
                    else:
                        return None
                else:
                    log.info(
                        f"Number of attempts: {retry} to get resource: "
                        f"{resource_name}, selector: {selector}, remain! "
                        f"Trying again in {wait} sec."
                    )
                    time.sleep(wait if wait else 1)

    @retry(ResourceWrongStatusException, tries=4, delay=5, backoff=1)
    def wait_for_phase(self, phase, timeout=300, sleep=5):
        """
        Wait till phase of resource is the same as required one passed in
        the phase parameter.
        Args:
            phase (str): Desired phase of resource object
            timeout (int): Timeout in seconds to wait for desired phase
            sleep (int): Time in seconds to sleep between attempts
        Raises:
            ResourceWrongStatusException: In case the resource is not in expected
                phase.
            NotSupportedFunctionError: If resource doesn't have phase!
            ResourceNameNotSpecifiedException: in case the name is not
                specified.
        """
        self.check_function_supported(self._has_phase)
        self.check_name_is_specified()
        sampler = TimeoutSampler(timeout, sleep, func=self.check_phase, phase=phase)
        if not sampler.wait_for_func_status(True):
            raise ResourceWrongStatusException(
                f"Resource: {self.resource_name} is not in expected phase: " f"{phase}"
            )

    def check_phase(self, phase):
        """
        Check phase of resource
        Args:
            phase (str): Phase of resource object
        Returns:
            bool: True if phase of object is the same as passed one, False
                otherwise.
        Raises:
            NotSupportedFunctionError: If resource doesn't have phase!
            ResourceNameNotSpecifiedException: in case the name is not
                specified.
        """
        self.check_function_supported(self._has_phase)
        self.check_name_is_specified()
        try:
            data = self.get()
        except CommandFailed:
            log.info(f"Cannot find resource object {self.resource_name}")
            return False
        try:
            current_phase = data["status"]["phase"]
            log.info(f"Resource {self.resource_name} is in phase: {current_phase}!")
            return current_phase == phase
        except KeyError:
            log.info(
                f"Problem while reading phase status of resource "
                f"{self.resource_name}, data: {data}"
            )
        return False

    def check_function_supported(self, support_var):
        """
        Check if the resource supports the functionality based on the
        support_var.
        Args:
            support_var (bool): True if functionality is supported, False
                otherwise.
        Raises:
            NotSupportedFunctionError: If support_var == False
        """
        if not support_var:
            raise NotSupportedFunctionError(
                "Resource name doesn't support this functionality!"
            )

    def exec_oc_cmd(
        self,
        command,
        out_yaml_format=True,
        timeout=600,
        ignore_error=False,
        silent=False,
        skip_tls_verify=False,
        **kwargs,
    ):
        """
        Executing 'oc' command
        Args:
            command (str): The command to execute (e.g. create -f file.yaml)
                without the initial 'oc' at the beginning
            out_yaml_format (bool): whether to return  yaml loaded python
                object or raw output
            secrets (list): A list of secrets to be masked with asterisks
                This kwarg is popped in order to not interfere with
                subprocess.run(``**kwargs``)
            timeout (int): timeout for the oc_cmd, defaults to 600 seconds
            ignore_error (bool): True if ignore non zero return code and do not
                raise the exception.
            silent (bool): If True will silent errors from the server, default false
            skip_tls_verify (bool): Adding '--insecure-skip-tls-verify' to oc command
        Returns:
            dict: Dictionary represents a returned yaml file.
            str: If out_yaml_format is False.
        """
        oc_cmd = "oc "
        env_kubeconfig = os.getenv("KUBECONFIG")
        kubeconfig_path = (
            self.cluster_kubeconfig if os.path.exists(self.cluster_kubeconfig) else None
        )

        if kubeconfig_path or not env_kubeconfig or not os.path.exists(env_kubeconfig):
            cluster_dir_kubeconfig = kubeconfig_path or os.path.join(
                config.ENV_DATA["cluster_path"], config.RUN.get("kubeconfig_location")
            )
            if os.path.exists(cluster_dir_kubeconfig):
                oc_cmd += f"--kubeconfig {cluster_dir_kubeconfig} "

        if self.namespace:
            oc_cmd += f"-n {self.namespace} "
        if skip_tls_verify or self.skip_tls_verify:
            command += " --insecure-skip-tls-verify"

        oc_cmd += command
        out = exec_cmd(
            cmd=oc_cmd,
            timeout=timeout,
            ignore_error=ignore_error,
            threading_lock=self.threading_lock,
            silent=silent,
            **kwargs,
        )
        if out_yaml_format:
            return yaml.safe_load(out.stdout)
        return out

    def get_resource(self, resource_name, column, retry=0, wait=3, selector=None):
        """
        Get a column value for a resource based on:
        'oc get <resource_kind> <resource_name>' command
        Args:
            resource_name (str): The name of the resource to get its column value
            column (str): The name of the column to retrive
            retry (int): Number of attempts to retry to get resource
            wait (int): Number of seconds to wait beteween attempts for retry
            selector (str): The resource selector to search with.
        Returns:
            str: The output returned by 'oc get' command not in the 'yaml'
                format
        """
        resource_name = resource_name if resource_name else self.resource_name
        selector = selector if selector else self.selector
        # Get the resource in str format
        resource = self.get(
            resource_name=resource_name,
            out_yaml_format=False,
            retry=retry,
            wait=wait,
            selector=selector,
        )
        resource = re.split(r"\s{2,}", resource)
        exception_list = ["RWO", "RWX", "ROX"]
        # get the list of titles
        titles = [i for i in resource if (i.isupper() and i not in exception_list)]

        # Get the values from the output including access modes in capital
        # letters
        resource_info = [
            i for i in resource if (not i.isupper() or i in exception_list)
        ]

        temp_list = shlex.split(resource_info.pop(0))

        for i in temp_list:
            if i.isupper():
                titles.append(i)
                temp_list.remove(i)
        resource_info = temp_list + resource_info

        # Fix for issue:
        # https://github.com/red-hat-storage/ocs-ci/issues/6503
        title_last_item = shlex.split(titles[-1])
        updated_last_title_item = []
        if len(title_last_item) > 1:
            for i in title_last_item:
                if i.isupper() and i not in exception_list:
                    updated_last_title_item.append(i)
                else:
                    resource_info.insert(0, i)
        if updated_last_title_item:
            titles[-1] = " ".join(updated_last_title_item)

        # Get the index of column
        column_index = titles.index(column)

        # WA, Failed to parse "oc get build" command
        # https://github.com/red-hat-storage/ocs-ci/issues/2312
        try:
            if self.data["items"][0]["kind"].lower() == "build" and (
                "jax-rs-build" in self.data["items"][0].get("metadata").get("name")
            ):
                return resource_info[column_index - 1]
        except Exception:
            pass

        return resource_info[column_index]

    def wait_for_resource(
        self,
        condition,
        resource_name="",
        column="STATUS",
        selector=None,
        resource_count=0,
        timeout=60,
        sleep=3,
        dont_allow_other_resources=False,
        error_condition=None,
    ):
        """
        Wait for a resource to reach to a desired condition
        Args:
            condition (str): The desired state the resource that is sampled
                from 'oc get <kind> <resource_name>' command
            resource_name (str): The name of the resource to wait
                for (e.g.my-pv1)
            column (str): The name of the column to compare with
            selector (str): The resource selector to search with.
                Example: 'app=rook-ceph-mds'
            resource_count (int): How many resources expected to be
            timeout (int): Time in seconds to wait
            sleep (int): Sampling time in seconds
            dont_allow_other_resources (bool): If True it will not allow other
                resources in different state. For example you are waiting for 2
                resources and there are currently 3 (2 in running state,
                1 in ContainerCreating) the function will continue to next
                iteration to wait for only 2 resources in running state and no
                other exists.
            error_condition (str): State of the resource that is sampled
                from 'oc get <kind> <resource_name>' command, which makes this
                method to fail immediately without waiting for a timeout. This
                is optional and makes sense only when there is a well defined
                unrecoverable state of the resource(s) which is not expected to
                be part of a workflow under test, and at the same time, the
                timeout itself is large.
        Returns:
            bool: True in case all resources reached desired condition,
                False otherwise
        """
        if condition == error_condition:
            # when this fails, this method is used in a wrong way
            raise ValueError(
                f"Condition '{condition}' we are waiting for must be different"
                f" from error condition '{error_condition}'"
                " which describes unexpected error state."
            )
        log.info(
            (
                f"Waiting for a resource(s) of kind {self._kind}"
                f" identified by name '{resource_name}'"
                f" using selector {selector}"
                f" at column name {column}"
                f" to reach desired condition {condition}"
            )
        )
        resource_name = resource_name if resource_name else self.resource_name
        selector = selector if selector else self.selector

        # actual status of the resource we are waiting for, setting it to None
        # now prevents UnboundLocalError raised when waiting timeouts
        actual_status = None

        try:
            for sample in TimeoutSampler(
                timeout, sleep, self.get, resource_name, True, selector
            ):
                # Only 1 resource expected to be returned
                if resource_name:
                    retry = int(timeout / sleep if sleep else timeout / 1)
                    status = self.get_resource(
                        resource_name,
                        column,
                        retry=retry,
                        wait=sleep,
                    )
                    if status == condition:
                        log.info(
                            f"status of {resource_name} at {column}"
                            " reached condition!"
                        )
                        return True
                    log.info(
                        (
                            f"status of {resource_name} at column {column} was {status},"
                            f" but we were waiting for {condition}"
                        )
                    )
                    actual_status = status
                    if error_condition is not None and status == error_condition:
                        raise ResourceWrongStatusException(
                            resource_name,
                            column=column,
                            expected=condition,
                            got=status,
                        )
                # More than 1 resources returned
                elif sample.get("kind") == "List":
                    in_condition = []
                    in_condition_len = 0
                    actual_status = []
                    sample = sample["items"]
                    sample_len = len(sample)
                    for item in sample:
                        try:
                            item_name = item.get("metadata").get("name")
                            status = self.get_resource(item_name, column)
                            actual_status.append(status)
                            if status == condition:
                                in_condition.append(item)
                                in_condition_len = len(in_condition)
                            if (
                                error_condition is not None
                                and status == error_condition
                            ):
                                raise ResourceWrongStatusException(
                                    item_name,
                                    column=column,
                                    expected=condition,
                                    got=status,
                                )
                        except CommandFailed as ex:
                            log.info(
                                f"Failed to get status of resource: {item_name} at column {column}, "
                                f"Error: {ex}"
                            )
                        if resource_count:
                            if in_condition_len == resource_count:
                                log.info(
                                    f"{in_condition_len} resources already "
                                    f"reached condition!"
                                )
                                if (
                                    dont_allow_other_resources
                                    and sample_len != in_condition_len
                                ):
                                    log.info(
                                        f"There are {sample_len} resources in "
                                        f"total. Continue to waiting as "
                                        f"you don't allow other resources!"
                                    )
                                    continue
                                return True
                        elif len(sample) == len(in_condition):
                            return True
                    # preparing logging message with expected number of
                    # resource items we are waiting for
                    if resource_count > 0:
                        exp_num_str = f"all {resource_count}"
                    else:
                        exp_num_str = "all"
                    log.info(
                        (
                            f"status of {resource_name} at column {column} - item(s) were {actual_status},"
                            f" but we were waiting"
                            f" for {exp_num_str} of them to be {condition}"
                        )
                    )
        except TimeoutExpiredError as ex:
            log.error(f"timeout expired: {ex}")
            # run `oc describe` on the resources we were waiting for to provide
            # evidence so that we can understand what was wrong
            output = self.describe(resource_name, selector=selector)
            log.warning(
                "Description of the resource(s) we were waiting for:\n%s", output
            )
            log.error(
                (
                    f"Wait for {self._kind} resource {resource_name} at column {column}"
                    f" to reach desired condition {condition} failed,"
                    f" last actual status was {actual_status}"
                )
            )
            raise (ex)
        except ResourceWrongStatusException:
            output = self.describe(resource_name, selector=selector)
            log.warning(
                "Description of the resource(s) we were waiting for:\n%s", output
            )
            log.error(
                (
                    "Waiting for %s resource %s at column %s"
                    " to reach desired condition %s was aborted"
                    " because at least one is in unexpected %s state."
                ),
                self._kind,
                resource_name,
                column,
                condition,
                error_condition,
            )
            raise

        return False

    def add_label(self, resource_name, label):
        """
        Adds a new label for this pod
        Args:
            resource_name (str): Name of the resource you want to label
            label (str): New label to be assigned for this pod
                E.g: "label=app='rook-ceph-mds'"
        """
        command = f"label {self.kind} {resource_name} {label} --overwrite "
        status = self.exec_oc_cmd(command)
        return status
