# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import pathlib
from typing import Optional, Union
from unittest import mock

import aiosqlite
import pytest

from ... import model
from ...components import yanking as yank_repository
from .fake_repository import FakeRepository


def test_yank_per_version() -> None:
    project_page = model.ProjectDetail(
        name="Project",
        meta=model.Meta("1.0"),
        files=(
            model.File(
              filename="Project-1.0.0-any.whl",
              url="url",
              hashes={},
            ),
            model.File(
              filename="Project-1.0.0.tar.gz",
              url="url",
              hashes={},
            ),
            model.File(
              filename="Project-1.0.1.tar.gz",
              url="url",
              hashes={},
            ),
        ),
    )

    yanked_versions = {"1.0.0": "reason"}
    yanked_page = yank_repository.add_yanked_attribute_per_version(
        project_page,
        yanked_versions,
    )
    assert yanked_page.files[0].yanked == "reason"
    assert yanked_page.files[1].yanked == "reason"
    assert yanked_page.files[2].yanked is None


def test_yank_per_file() -> None:
    project_page = model.ProjectDetail(
        name="Project",
        meta=model.Meta("1.0"),
        files=(
            model.File(
              filename="project-1.0.0-any.whl",
              url="url",
              hashes={},
            ),
            model.File(
              filename="Project-1.0.0.tar.gz",
              url="url",
              hashes={},
            ),
            model.File(
              filename="Project-1.0.1.tar.gz",
              url="url",
              hashes={},
            ),
        ),
    )

    yanked_versions = {"project-1.0.0-any.whl": "reason"}
    yanked_page = yank_repository.add_yanked_attribute_per_file(
        project_page,
        yanked_versions,
    )
    assert yanked_page.files[0].yanked == "reason"
    assert yanked_page.files[1].yanked is None
    assert yanked_page.files[2].yanked is None


@pytest.mark.parametrize(
    "yanked_versions, yanked_value", [
        ({}, None),
        ({"1.0": "reason"}, "reason"),
        ({"1.0": ""}, True),
    ],
)
@pytest.mark.asyncio
async def test_get_project_page(
    yanked_versions: dict[str, str],
    yanked_value: Optional[Union[bool, str]],
) -> None:
    repository = yank_repository.YankRepository(
        FakeRepository(
            project_pages=[
                model.ProjectDetail(
                    model.Meta("1.0"), name="project", files=(
                        model.File("project-1.0-anylinux.whl", "url", {}),
                        model.File("project-1.0.tar.gz", "url", {}),
                        model.File("project-1.1.tar.gz", "url", {}),
                    ),
                ),
            ],
        ),
        mock.AsyncMock(),
    )

    with mock.patch(
        "simple_repository.components.yanking.get_yanked_versions",
        return_value=yanked_versions,
    ):
        result = await repository.get_project_page("project")

    assert result.files[0].yanked == yanked_value
    assert result.files[1].yanked == yanked_value
    assert result.files[2].yanked is None


@pytest.mark.asyncio
async def test_get_yanked_versions(tmp_path: pathlib.Path) -> None:
    database_path = tmp_path / "temp.db"
    async with aiosqlite.connect(database_path) as database:
        await yank_repository.YankRepository(
            source=FakeRepository(),
            database=database,
        )._init_db()
        await database.execute(
            "CREATE TABLE IF NOT EXISTS yanked_versions"
            "(project_name TEXT, version TEXT, reason TEXT"
            ", CONSTRAINT pk PRIMARY KEY (project_name, version))",
        )
        await database.execute(
            "INSERT INTO yanked_versions (project_name, version, reason)"
            " VALUES(:project_name, :version, :reason)",
            {"project_name": "project", "version": "1.0", "reason": "reason1"},
        )
        await database.execute(
            "INSERT INTO yanked_versions (project_name, version, reason)"
            " VALUES(:project_name, :version, :reason)",
            {"project_name": "project", "version": "2.0", "reason": "reason2"},
        )

        await database.commit()

        versions = await yank_repository.get_yanked_versions("project", database)

    assert versions == {"1.0": "reason1", "2.0": "reason2"}
