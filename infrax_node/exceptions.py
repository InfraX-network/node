class NodeRegistrationFailureException(Exception):
    pass


class JobAlreadyExistsException(Exception):
    pass


class NodeNotFoundException(Exception):
    pass


class AppNotFoundException(Exception):
    pass


class AppFailedToInstallException(Exception):
    pass


class AppFailedToUninstallException(Exception):
    pass
