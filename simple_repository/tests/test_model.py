# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

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
