# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import enum
import posixpath
import typing

import packaging.utils
import packaging.version


def split_sdist_filename(path: str) -> typing.Tuple[str, str]:
    """
    Like os.path.splitext, but take off .tar too.
    Standard functions like splitext or pathlib suffixes
    will fail to extract the extension of sdists
    like numpy-1.0.0.tar.gz
    """
    base, ext = posixpath.splitext(path)
    if base.lower().endswith(".tar"):
        ext = base[-4:] + ext
        base = base[:-4]
    return base, ext


class PackageFormat(enum.Enum):
    WHEEL = "wheel"
    SDIST = "sdist"
    OTHER = "other format"


def extract_package_format(filename: str) -> PackageFormat:
    _, file_format = split_sdist_filename(filename)
    if file_format == ".whl":
        return PackageFormat.WHEEL
    if file_format in (".zip", ".tar.gz", ".tar.bz2", ".tar.xz", ".tar.Z", ".tar"):
        return PackageFormat.SDIST
    # .egg files and other legacy formats are OTHER
    return PackageFormat.OTHER


def extract_version_from_fragment(fragment: str, project_name: str) -> str:
    def find_version_start() -> int:
        pieces = fragment.split("-")
        for i in range(len(pieces)):
            candidate = "-".join(pieces[0:i])
            if packaging.utils.canonicalize_name(candidate) == project_name:
                return len(candidate)
        raise ValueError(f"{fragment} does not match {project_name}")

    version = fragment[find_version_start() + 1 :]
    # Drop trailing parts (e.g. openpyxl-1.1.0-py2.6.egg)
    version = version.split("-", 1)[0]
    return version


def extract_package_version(filename: str, project_name: str) -> str:
    if extract_package_format(filename) == PackageFormat.WHEEL:
        return filename.split("-")[1]
    else:
        fragment, _ = split_sdist_filename(filename)
        return extract_version_from_fragment(fragment, project_name)


def safe_version(filename: str, project_name: str) -> packaging.version.Version:
    try:
        return packaging.version.Version(
            version=extract_package_version(
                filename=filename,
                project_name=project_name,
            ),
        )
    except (ValueError, packaging.version.InvalidVersion):
        return packaging.version.Version("0.0rc0")
