class ClusterNotFoundException(Exception):
    pass

class UnSupportedPlatformException(Exception):
    pass

class UnsupportedOSType(Exception):
    pass

class CommandFailed(Exception):
    pass

class ClientDownloadError(Exception):
    pass

class PullSecretNotFoundException(Exception):
    pass