# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import dataclasses

import pytest

from .. import model


def test_ProjectListElement__normalized_name() -> None:
    prj = model.ProjectListElement('some-.name')
    assert prj.normalized_name == 'some-name'


def test_ProjectDetail__normalized_name() -> None:
    project_detail = model.ProjectDetail(
        meta=model.Meta("1.0"),
        name="Project",
        files=(),
    )
    assert project_detail._normalized_name == "project"


def test_ProjectDetail__failed_post_init() -> None:
    with pytest.raises(
        ValueError,
        match="SimpleAPI>=1.1 requires the size field to be set for all the files.",
    ):
        model.ProjectDetail(
            meta=model.Meta("1.1"),
            name="pippo",
            files=(
                model.File(
                    filename="pippozzo",
                    url="url",
                    hashes={},
                ),
            ),
        )


def test_ProjectDetail__post_init_v1() -> None:
    project_detail = model.ProjectDetail(
        meta=model.Meta("1.0"),
        name="pippo",
        files=(
            model.File(
                filename="pippozzo",
                url="url",
                hashes={},
            ),
        ),
    )
    assert project_detail.versions is None


def test_ProjectDetail__post_init_v1_1() -> None:
    project_detail = model.ProjectDetail(
        meta=model.Meta("1.1"),
        name="pippo",
        files=(
            model.File(
                filename="pippo-1.0.tar.gz",
                url="url",
                hashes={},
                size=1,
            ),
            model.File(
                filename="pippo-2.0-anylinux-py3.whl",
                url="url",
                hashes={},
                size=1,
            ),
        ),
    )
    assert project_detail.versions == {
        "1.0", "2.0",
    }


def test_ProjectDetail__versions_subset() -> None:
    message = (
        'The versions specified in ProjectDetail does not include all of '
        'the versions that can be found in the files'
    )
    with pytest.raises(ValueError, match=message):
        model.ProjectDetail(
            meta=model.Meta("1.1"),
            name="pippo",
            files=(
                model.File(
                    filename="pippo-1.0.tar.gz",
                    url="url",
                    hashes={},
                    size=1,
                ),
                model.File(
                    filename="pippo-2.0-anylinux-py3.whl",
                    url="url",
                    hashes={},
                    size=1,
                ),
            ),
            versions={'1.0'},
        )


def test_ProjectDetail__manual_versions() -> None:
    # Sometimes we want to be able to state that there are versions with no
    # files (PEP-700):
    # > The versions key MAY contain versions with no associated files
    project_detail = model.ProjectDetail(
        meta=model.Meta("1.1"),
        name="pippo",
        files=(
            model.File(
                filename="pippo-1.0.tar.gz",
                url="url",
                hashes={},
                size=1,
            ),
            model.File(
                filename="pippo-2.0-anylinux-py3.whl",
                url="url",
                hashes={},
                size=1,
            ),
        ),
    )
    assert project_detail.versions == {'1.0', '2.0'}
    pd2 = dataclasses.replace(project_detail, versions=project_detail.versions | {'1.2.3'})
    # Now check that it persists with some other replacement.
    pd3 = dataclasses.replace(pd2)

    assert pd2.versions == {
        "1.0", "2.0", "1.2.3",
    }
    assert pd2.versions == pd3.versions


def test__File__arbitrary_private_metadata() -> None:
    file = model.File(
        filename="pippo",
        url="url",
        hashes={},
        _foo='bar',
    )
    assert file._foo == 'bar'
    # Ensure that the private attributes survives additional public attribute
    # changes.
    new_file = dataclasses.replace(file, filename='bar')
    assert new_file._foo == 'bar'


def test__File__eq__private_metadata() -> None:
    file = model.File(
        filename="pippo",
        url="url",
        hashes={},
        _foo='bar',
    )
    file2 = model.File(
        filename="pippo",
        url="url",
        hashes={},
    )
    assert file != file2
    assert file == file


@pytest.mark.xfail(strict=True)
def test__File__hash__private_metadata() -> None:
    file = model.File(
        filename="pippo",
        url="url",
        hashes={},
        _foo='bar',
    )
    file2 = model.File(
        filename="pippo",
        url="url",
        hashes={},
    )
    assert hash(file) != hash(file2)


@pytest.mark.xfail(strict=True)
def test__File__hash() -> None:
    file = model.File(
        filename="pippo",
        url="url",
        hashes={},
    )
    # The file should be hashable (it is frozen after all), but we currently
    # allow dict to be passed.
    hash(file)


def test__File__no_arbitrary_public_metadata() -> None:
    with pytest.raises(TypeError, match=r'unexpected keyword argument .?foo.?'):
        model.File(
            filename="pippo",
            url="url",
            hashes={},
            foo='bar',
        )
