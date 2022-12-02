import requests
import json
import logging
import os
import platform
import shlex
import subprocess

from semantic_version import Version
from src.utility.defaults import (
    DEFAULT_BIN_DIR,
    DEFAULT_INSTALLER_VERSION,
    DEFAULT_OPENSHIFT_CLIENT_VERSION
)
from src.exceptions.ocp_exceptions import (
    UnsupportedOSType,
    CommandFailed,
    ClientDownloadError
)


logger = logging.getLogger(__name__)


def download_installer(
    version=None,
    bin_dir=None,
    force_download=False,
    config=None
):
    version = version or DEFAULT_INSTALLER_VERSION
    bin_dir = bin_dir or DEFAULT_BIN_DIR
    installer_filename = "openshift-install"
    installer_binary_path = os.path.join(bin_dir, installer_filename)
    if os.path.isfile(installer_binary_path) and force_download:
        delete_file(installer_binary_path)
    if os.path.isfile(installer_binary_path):
        logger.debug(f"Installer exists ({installer_binary_path}), skipping download.")
        # TODO: check installer version
    else:
        version = expose_ocp_version(version)
        logger.info(f"Downloading openshift installer ({version}).")
        prepare_bin_dir(config=config)
        # record current working directory and switch to BIN_DIR
        previous_dir = os.getcwd()
        os.chdir(bin_dir)
        tarball = f"{installer_filename}.tar.gz"
        url = get_openshift_mirror_url(installer_filename, version, config)
        download_file(url, tarball)
        exec_cmd(f"tar xzvf {tarball} {installer_filename}")
        delete_file(tarball)
        # return to the previous working directory
        os.chdir(previous_dir)

    installer_version = exec_cmd(f"{installer_binary_path} version")
    logger.info(f"OpenShift Installer version: {installer_version}")
    return installer_binary_path


def get_openshift_client(
    version=None, bin_dir=None, force_download=False, skip_comparison=False, config=None
):
    """
    Download the OpenShift client binary, if not already present.
    Update env. PATH and get path of the oc binary.
    Args:
        version (str): Version of the client to download
            (default: config.RUN['client_version'])
        bin_dir (str): Path to bin directory (default: config.RUN['bin_dir'])
        force_download (bool): Force client download even if already present
        skip_comparison (bool): Skip the comparison between the existing OCP client
            version and the configured one.
    Returns:
        str: Path to the client binary
    """
    version = version or DEFAULT_OPENSHIFT_CLIENT_VERSION
    bin_dir = os.path.expanduser(config.RUN["bin_dir"] or DEFAULT_BIN_DIR)
    client_binary_path = os.path.join(bin_dir, "oc")
    download_client = True
    client_version = None
    try:
        version = expose_ocp_version(version, config)
    except Exception:
        logger.exception("Unable to expose OCP version, skipping client download.")
        skip_comparison = True
        download_client = False
        force_download = False
    if force_download:
        logger.info("Forcing client download.")
    elif os.path.isfile(client_binary_path) and not skip_comparison:
        current_client_version = get_client_version(client_binary_path)
        if current_client_version != version:
            logger.info(
                f"Existing client version ({current_client_version}) does not match "
                f"configured version ({version})."
            )
        else:
            logger.debug(
                f"Client exists ({client_binary_path}) and matches configured version, "
                f"skipping download."
            )
            download_client = False
    if download_client:
        # Move existing client binaries to backup location
        client_binary_backup = f"{client_binary_path}.bak"

        try:
            os.rename(client_binary_path, client_binary_backup)
        except FileNotFoundError:
            pass

        # Download the client
        logger.info(f"Downloading openshift client ({version}).")
        prepare_bin_dir(config=config)
        # record current working directory and switch to BIN_DIR
        previous_dir = os.getcwd()
        os.chdir(bin_dir)
        url = get_openshift_mirror_url("openshift-client", version, config)
        tarball = "openshift-client.tar.gz"
        download_file(url, tarball)
        exec_cmd(f"tar xzvf {tarball} oc kubectl")
        delete_file(tarball)

        try:
            client_version = exec_cmd(f"{client_binary_path} version --client")
        except CommandFailed:
            logger.error("Unable to get version from downloaded client.")

        if client_version:
            try:
                delete_file(client_binary_backup)
                logger.info("Deleted backup binaries.")
            except FileNotFoundError:
                pass
        else:
            try:
                os.rename(client_binary_backup, client_binary_path)
                logger.info("Restored backup binaries to their original location.")
            except FileNotFoundError:
                raise ClientDownloadError(
                    "No backups exist and new binary was unable to be verified."
                )

        # return to the previous working directory
        os.chdir(previous_dir)

    logger.info(f"OpenShift Client version: {client_version}")
    return client_binary_path


def expose_ocp_version(version, config=None):
    """
        This helper function exposes latest nightly version or GA version of OCP.
        When the version string ends with .nightly (e.g. 4.2.0-0.nightly) it will
        expose the version to latest accepted OCP build
        (e.g. 4.2.0-0.nightly-2019-08-08-103722)
        If the version ends with -ga than it will find the latest GA OCP version
        and will expose 4.2-ga to for example 4.2.22.
        Args:
            version (str): Verison of OCP
        Returns:
            str: Version of OCP exposed to full version if latest nighly passed
    """
    if version.endswith(".nightly"):
        latest_nightly_url = (
            f"https://amd64.ocp.releases.ci.openshift.org/api/v1/"
            f"releasestream/{version}/latest"
        )
        version_url_content = get_url_content(latest_nightly_url)
        version_json = json.loads(version_url_content)
        return version_json["name"]
    if version.endswith("-ga"):
        channel = config.DEPLOYMENT.get("ocp_channel", "stable")
        ocp_version = version.rstrip("-ga")
        index = config.DEPLOYMENT.get("ocp_version_index", -1)
        return get_latest_ocp_version(f"{channel}-{ocp_version}", index)
    else:
        return version


def get_available_ocp_versions(channel):
    """
    Find all available OCP versions for specific channel.
    Args:
        channel (str): Channel of OCP (e.g. stable-4.2 or fast-4.2)
    Returns
        list: Sorted list with OCP versions for specified channel.
    """
    headers = {"Accept": "application/json"}
    req = requests.get(
        "https://api.openshift.com/api/upgrades_info/v1/graph?channel={channel}".format(channel=channel), headers=headers
    )
    data = req.json()
    versions = [Version(node["version"]) for node in data["nodes"]]
    versions.sort()
    return versions

def get_latest_ocp_version(channel, index=-1):
    """
    Find latest OCP version for specific channel.
    Args:
        channel (str): Channel of OCP (e.g. stable-4.2 or fast-4.2)
        index (int): Index to get from all available versions list
            e.g. default -1 is latest version (version[-1]). If you want to get
            previous version pass index -2 and so on.
    Returns
        str: Latest OCP version for specified channel.
    """
    versions = get_available_ocp_versions(channel)
    return str(versions[index])

def get_url_content(url, **kwargs):
    """
    Return URL content
    Args:
        url (str): URL address to return
        kwargs (dict): additional keyword arguments passed to requests.get(...)
    Returns:
        str: Content of URL
    Raises:
        AssertionError: When couldn't load URL
    """
    logger.debug(f"Download '{url}' content.")
    r = requests.get(url, **kwargs)
    assert r.ok, f"Couldn't load URL: {url} content! Status: {r.status_code}."
    return r.content

def delete_file(file_name):
    """
    Delete file_name
    Args:
        file_name (str): Path to the file you want to delete
    """
    os.remove(file_name)

def prepare_bin_dir(bin_dir=None, config=None):
    """
    Prepare bin directory for OpenShift client and installer
    Args:
        bin_dir (str): Path to bin directory (default: config.RUN['bin_dir'])
    """
    bin_dir = os.path.expanduser(bin_dir or config.RUN["bin_dir"])
    try:
        os.mkdir(bin_dir)
        logger.info(f"Directory '{bin_dir}' successfully created.")
    except FileExistsError:
        logger.debug(f"Directory '{bin_dir}' already exists.")

def get_openshift_mirror_url(file_name, version, config=None):
    """
    Format url to OpenShift mirror (for client and installer download).
    Args:
        file_name (str): Name of file
        version (str): Version of the installer or client to download
    Returns:
        str: Url of the desired file (installer or client)
    Raises:
        UnsupportedOSType: In case the OS type is not supported
        UnavailableBuildException: In case the build url is not reachable
    """
    if platform.system() == "Darwin":
        os_type = "mac"
    elif platform.system() == "Linux":
        os_type = "linux"
    else:
        raise UnsupportedOSType
    url_template = config.DEPLOYMENT.get(
        "ocp_url_template",
        "https://openshift-release-artifacts.apps.ci.l2s4.p1.openshiftapps.com/"
        "{version}/{file_name}-{os_type}-{version}.tar.gz",
    )
    url = url_template.format(
        version=version,
        file_name=file_name,
        os_type=os_type,
    )
    return url

def download_file(url, filename, **kwargs):
    """
    Download a file from a specified url
    Args:
        url (str): URL of the file to download
        filename (str): Name of the file to write the download to
        kwargs (dict): additional keyword arguments passed to requests.get(...)
    """
    logger.debug(f"Download '{url}' to '{filename}'.")
    with open(filename, "wb") as f:
        r = requests.get(url, **kwargs)
        assert r.ok, f"The URL {url} is not available! Status: {r.status_code}."
        f.write(r.content)


def exec_cmd(
    cmd,
    timeout=600,
    ignore_error=False,
    threading_lock=None,
    silent=False,
    **kwargs,
):
    """
        Run an arbitrary command locally
        If the command is grep and matching pattern is not found, then this function
        returns "command terminated with exit code 1" in stderr.
        Args:
            cmd (str): command to run
            timeout (int): Timeout for the command, defaults to 600 seconds.
            ignore_error (bool): True if ignore non zero return code and do not
                raise the exception.
            threading_lock (threading.Lock): threading.Lock object that is used
                for handling concurrent oc commands
            silent (bool): If True will silent errors from the server, default false
        Raises:
            CommandFailed: In case the command execution fails
        Returns:
            (CompletedProcess) A CompletedProcess object of the command that was executed
            CompletedProcess attributes:
            args: The list or str args passed to run().
            returncode (str): The exit code of the process, negative for signals.
            stdout     (str): The standard output (None if not captured).
            stderr     (str): The standard error (None if not captured).
    """

    logger.info(f"Executing command: {cmd}")
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    if threading_lock and cmd[0] == "oc":
        threading_lock.acquire()
    completed_process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        timeout=timeout,
        **kwargs,
    )
    if threading_lock and cmd[0] == "oc":
        threading_lock.release()
    stdout = completed_process.stdout.decode()
    stdout_err = completed_process.stderr.decode()
    if len(completed_process.stdout) > 0:
        logger.debug(f"Command stdout: {stdout}")
    else:
        logger.debug("Command stdout is empty")
    if len(completed_process.stderr) > 0:
        if not silent:
            logger.warning(f"Command stderr: {stdout_err}")
    else:
        logger.debug("Command stderr is empty")
    logger.debug(f"Command return code: {completed_process.returncode}")
    if completed_process.returncode and not ignore_error:
        if (
                "grep" in cmd
                and b"command terminated with exit code 1" in completed_process.stderr
        ):
            logger.info(f"No results found for grep command: {cmd}")
        else:
            raise CommandFailed(
                f"Error during execution of command: {cmd}."
                f"\nError is {stdout_err}"
            )
    return completed_process

def get_client_version(client_binary_path):
    """
    Get version reported by `oc version`.
    Args:
        client_binary_path (str): path to `oc` binary
    Returns:
        str: version reported by `oc version`.
            None if the client does not exist at the provided path.
    """
    if os.path.isfile(client_binary_path):
        cmd = f"{client_binary_path} version --client -o json"
        resp = exec_cmd(cmd)
        stdout = json.loads(resp.stdout.decode())
        return stdout["releaseClientVersion"]


def ocp4mcoci_log_path(config=None):
    """
    Construct the full path for the log directory.
    Returns:
        str: full path for ocp4mco-ci log directory
    """
    return os.path.expanduser(
        os.path.join(config.RUN["log_dir"], f"ocp4mco-ci-logs-{config.RUN['run_id']}")
    )

def add_path_to_env_path(path):
    """
    Add path to the PATH environment variable (if not already there).
    Args:
        path (str): Path which should be added to the PATH env. variable
    """
    env_path = os.environ["PATH"].split(os.pathsep)
    if path not in env_path:
        os.environ["PATH"] = os.pathsep.join([path] + env_path)
        logger.info(f"Path '{path}' added to the PATH environment variable.")
    logger.debug(f"PATH: {os.environ['PATH']}")

def create_directory_path(path):
    """
    Creates directory if path doesn't exists
    """
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        os.makedirs(path)
    else:
        logger.debug(f"{path} already exists")
