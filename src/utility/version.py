from semantic_version import Version
from src.framework import config


def get_semantic_version(version, only_major_minor=False, ignore_pre_release=False):
    """
    Returning semantic version from provided version as string.
    Args:
        version (str): String version (e.g. 4.6)
        only_major_minor (bool): If True, only major and minor will be parsed.
        ignore_pre_release (bool): If True, the pre release version will be ignored
    Returns:
       semantic_version.base.Version: Object of semantic version.
    """
    version = Version.coerce(version)
    if only_major_minor:
        version.patch = None
        version.prerelease = None
    elif ignore_pre_release:
        version.prerelease = None
    return version


# Version constants
VERSION_4_2 = get_semantic_version("4.2", True)
VERSION_4_3 = get_semantic_version("4.3", True)
VERSION_4_4 = get_semantic_version("4.4", True)
VERSION_4_5 = get_semantic_version("4.5", True)
VERSION_4_6 = get_semantic_version("4.6", True)
VERSION_4_7 = get_semantic_version("4.7", True)
VERSION_4_8 = get_semantic_version("4.8", True)
VERSION_4_9 = get_semantic_version("4.9", True)
VERSION_4_10 = get_semantic_version("4.10", True)
VERSION_4_11 = get_semantic_version("4.11", True)
VERSION_4_12 = get_semantic_version("4.12", True)
VERSION_4_13 = get_semantic_version("4.13", True)
VERSION_4_14 = get_semantic_version("4.14", True)
VERSION_4_15 = get_semantic_version("4.15", True)
VERSION_4_16 = get_semantic_version("4.16", True)
VERSION_4_17 = get_semantic_version("4.17", True)
VERSION_4_18 = get_semantic_version("4.18", True)
VERSION_4_19 = get_semantic_version("4.19", True)


def get_semantic_ocs_version_from_config():
    """
    Returning OCS semantic version from config.
    Returns:
       semantic_version.base.Version: Object of semantic version for OCS.
    """
    return get_semantic_version(config.ENV_DATA["ocs_version"], True)
