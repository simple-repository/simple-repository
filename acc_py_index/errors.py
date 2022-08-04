class MissingHrefError(Exception):
    pass


class PackageNotFoundError(ValueError):
    msg_format = (
        "Package '{package_name}' was not found in the configured sources: {sources}"
    )

    def __init__(self, package_name: str, sources: list[str], *args: object):
        self.package_name = package_name
        self.sources = sources
        self.msg = self.msg_format.format(package_name=package_name, sources=sources)
        super().__init__(self.msg, *args)
