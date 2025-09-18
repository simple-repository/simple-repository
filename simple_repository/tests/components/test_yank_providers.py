# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import pathlib

import aiosqlite
import pytest

from ... import errors, model
from ...components.yanking import GlobYankProvider, SqliteYankProvider


@pytest.fixture
def project_page() -> model.ProjectDetail:
    return model.ProjectDetail(
        model.Meta("1.0"),
        "project",
        (
            model.File("project-1.0.whl", "url", {}),
            model.File("project-1.0.tar.gz", "url", {}),
        ),
    )


@pytest.mark.asyncio
async def test_glob_provider__yanked_files(
    tmp_path: pathlib.Path,
    project_page: model.ProjectDetail,
) -> None:
    file = tmp_path / "yank_config.json"
    file.write_text(
        data='{"project": ["*.whl", "bad"], "pandas": ["*[!.whl]", "not supported"]}',
    )

    provider = GlobYankProvider(yank_config_file=file)

    res = await provider.yanked_files(project_page)
    assert {"project-1.0.whl": "bad"} == res


@pytest.mark.asyncio
async def test_glob_provider__yanked_versions(
    tmp_path: pathlib.Path,
    project_page: model.ProjectDetail,
) -> None:
    file = tmp_path / "yank_config.json"
    file.write_text(
        data='{"numpy": ["*.whl", "bad"], "pandas": ["*[!.whl]", "not supported"]}',
    )

    provider = GlobYankProvider(yank_config_file=file)

    res = await provider.yanked_versions(project_page)
    assert {} == res


@pytest.mark.parametrize(
    "json_string",
    [
        "42",
        "true",
        '["a", "b"]',
        "null",
        '"ciao"',
    ],
)
def test_load_config_wrong_type(
    json_string: str,
    tmp_path: pathlib.PosixPath,
) -> None:
    file = tmp_path / "yank_config.json"
    file.write_text(
        data=json_string,
    )
    with pytest.raises(
        errors.InvalidConfigurationError,
        match=(f"Invalid configuration file. {str(file)} must contain a dictionary."),
    ):
        GlobYankProvider(yank_config_file=file)


def test_load_config_wrong_format(
    tmp_path: pathlib.PosixPath,
) -> None:
    file = tmp_path / "yank_config.json"
    file.write_text(
        data='{"a": "b"}',
    )
    with pytest.raises(
        errors.InvalidConfigurationError,
        match=(
            f"Invalid yank configuration file. {str(file)} must"
            " contain a dictionary mapping a project name to a tuple"
            " containing a glob pattern and a yank reason."
        ),
    ):
        GlobYankProvider(yank_config_file=file)


def test_load_config_malformed_json(
    tmp_path: pathlib.PosixPath,
) -> None:
    file = tmp_path / "yank_config.json"
    file.write_text(
        data="a",
    )
    with pytest.raises(
        errors.InvalidConfigurationError,
        match="Invalid json file",
    ):
        GlobYankProvider(yank_config_file=file)


@pytest.mark.asyncio
async def test_sqlite_provider__yanked_versions(
    tmp_path: pathlib.Path,
    project_page: model.ProjectDetail,
) -> None:
    database_path = tmp_path / "temp.db"
    async with aiosqlite.connect(database_path) as database:
        provider = SqliteYankProvider(database)
        await provider._init_db()
        await provider._database.executemany(
            "INSERT INTO yanked_versions (project_name, version, reason)"
            " VALUES(:project_name, :version, :reason)",
            [
                {"project_name": "project", "version": "1.0", "reason": "reason1"},
                {"project_name": "project", "version": "2.0", "reason": "reason2"},
            ],
        )

        await provider._database.commit()

        versions = await provider.yanked_versions(project_page)

    assert versions == {"1.0": "reason1", "2.0": "reason2"}


@pytest.mark.asyncio
async def test_sqlite_provider__yanked_files(
    tmp_path: pathlib.Path,
    project_page: model.ProjectDetail,
) -> None:
    database_path = tmp_path / "temp.db"
    async with aiosqlite.connect(database_path) as database:
        provider = SqliteYankProvider(database)
        await provider._init_db()
        await provider._database.executemany(
            "INSERT INTO yanked_releases (project_name, file_name, reason)"
            " VALUES(:project_name, :filename, :reason)",
            [
                {
                    "project_name": "project",
                    "filename": "project-1.0.whl",
                    "reason": "reason1",
                },
                {
                    "project_name": "project",
                    "filename": "project-2.0.whl",
                    "reason": "reason2",
                },
            ],
        )

        await provider._database.commit()

        versions = await provider.yanked_files(project_page)

    assert versions == {"project-1.0.whl": "reason1", "project-2.0.whl": "reason2"}
