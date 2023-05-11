class PackageNotFoundError(LookupError):
    msg_format = (
        "Package '{package_name}' was not found in the configured source"
    )

    def __init__(self, package_name: str, *args: object):
        msg = self.msg_format.format(package_name=package_name)
        super().__init__(msg, *args)


class SourceRepositoryUnavailable(Exception):
    pass


class NotNormalizedProjectName(Exception):
    pass


class UnsupportedSerialization(Exception):
    pass


class ResourceUnavailable(LookupError):
    msg_format = (
        "Resource '{resource_name}' was not found in the configured source"
    )

    def __init__(self, resource_name: str, *args: object):
        msg = self.msg_format.format(resource_name=resource_name)
        super().__init__(msg, *args)
