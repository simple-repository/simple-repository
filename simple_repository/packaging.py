# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import enum
import posixpath

import packaging.utils
from packaging.version import InvalidVersion, Version


def split_sdist_filename(path: str) -> tuple[str, str]:
    """
    Like os.path.splitext, but take off .tar too.
    Standard functions like splitext or pathlib suffixes
    will fail to extract the extention of sdists
    like numpy-1.0.0.tar.gz
    """
    base, ext = posixpath.splitext(path)
    if base.lower().endswith(".tar"):
        ext = base[-4:] + ext
        base = base[:-4]
    return base, ext


class PackageFormat(enum.Enum):
    WHEEL: str = "wheel"
    SDIST: str = "sdist"
    OTHER: str = "other format"


def extract_package_format(filename: str) -> PackageFormat:
    _, file_format = split_sdist_filename(filename)
    if file_format == ".whl":
        return PackageFormat.WHEEL
    if file_format in ('.zip', '.tar.gz', '.tar.bz2', '.tar.xz', '.tar.Z', '.tar'):
        return PackageFormat.SDIST
    return PackageFormat.OTHER


def extract_version_from_fragment(fragment: str, project_name: str) -> str:
    def find_version_start() -> int:
        pieces = fragment.split("-")
        for i in range(len(pieces)):
            candidate = "-".join(pieces[0:i])
            if packaging.utils.canonicalize_name(candidate) == project_name:
                return len(candidate)
        raise ValueError(f"{fragment} does not match {project_name}")
    return fragment[find_version_start() + 1:]


def extract_package_version(filename: str, project_name: str) -> str:
    if extract_package_format(filename) == PackageFormat.WHEEL:
        return filename.split('-')[1]
    else:
        fragment, _ = split_sdist_filename(filename)
        return extract_version_from_fragment(fragment, project_name)


def safe_version(filename: str, project_name: str) -> Version:
    try:
        return Version(
            version=extract_package_version(
                filename=filename,
                project_name=project_name,
            ),
        )
    except (ValueError, InvalidVersion):
        return Version('0.0rc0')
