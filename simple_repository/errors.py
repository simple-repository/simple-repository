# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations


class PackageNotFoundError(LookupError):
    msg_format = "Package '{package_name}' was not found in the configured source"

    def __init__(self, package_name: str, *args: object) -> None:
        msg = self.msg_format.format(package_name=package_name)
        super().__init__(msg, *args)


class SourceRepositoryUnavailable(Exception):
    pass


class NotNormalizedProjectName(Exception):
    # NOTE: This is not used, and is pending removal.
    #       Potential to move to simple-repository-server.
    pass


class UnsupportedSerialization(ValueError):
    msg_format = "Unsupported format '{format_name}'."

    def __init__(self, format_name: str, *args: object) -> None:
        msg = self.msg_format.format(format_name=format_name)
        super().__init__(msg, *args)


class UnsupportedAPIVersion(Exception):
    pass


class ResourceUnavailable(LookupError):
    msg_format = "Resource '{resource_name}' was not found in the configured source"

    def __init__(self, resource_name: str, *args: object) -> None:
        msg = self.msg_format.format(resource_name=resource_name)
        super().__init__(msg, *args)


class InvalidConfigurationError(ValueError):
    pass


class InvalidPackageError(ValueError):
    pass
