# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from packaging.version import Version
import pytest

from .. import packaging


@pytest.mark.parametrize(
        ("filename", "package_version"), [
            ("my_package1-0.0.1-any.whl", "0.0.1"),
            ("my-package1-0.0.1.tar.gz", "0.0.1"),
            ("my-package1-0.10.zip", "0.10"),
        ],
)
def test_extract_package_version(filename: str, package_version: str | None) -> None:
    assert packaging.extract_package_version(filename, "my-package1") == package_version


def test_extract_package_version_failed() -> None:
    with pytest.raises(
        ValueError,
        match="hello-0.1 does not match non_matching",
    ):
        packaging.extract_package_version("hello-0.1.zip", "non_matching")


@pytest.mark.parametrize(
        ("filename", "package_format"), [
            ("my_package-0.0.1-any.whl", "wheel"),
            ("my-package-0.0.1.tar.gz", "sdist"),
            ("my-package-0.0.1.jpeg", "other format"),
        ],
)
def test_extract_package_format(filename: str, package_format: str) -> None:
    assert packaging.extract_package_format(filename).value == package_format


@pytest.mark.parametrize(
    "filename, project_name, version", [
        ("numpy-1.6.0-cp26-cp26m-manylinux1_x86_64.whl", "numpy", Version("1.6.0")),
        ("numpy-1.6.0.tar.gz", "numpy", Version("1.6.0")),
        ("numpy-1.6.0.tar.gz", "tensorflow", Version("0.0rc0")),
        ("numpy-aaaa.whl", "numpy", Version("0.0rc0")),
        ("numpy-aaaa.tar.gz", "numpy", Version("0.0rc0")),
    ],
)
def test__safe_version(
    filename: str,
    project_name: str,
    version: Version,
) -> None:
    assert packaging.safe_version(filename, project_name) == version
