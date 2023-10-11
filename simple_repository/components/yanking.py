# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from dataclasses import replace
import fnmatch
import html
import pathlib
import typing

import aiosqlite
from packaging.utils import canonicalize_name

from .. import errors, model, packaging, utils
from .core import RepositoryContainer, SimpleRepository


async def get_yanked_versions(project_name: str, database: aiosqlite.Connection) -> dict[str, str]:
    query = "SELECT version, reason FROM yanked_versions WHERE project_name = :project_name"
    async with database.execute(query, {"project_name": project_name}) as cur:
        result = await cur.fetchall()
    return {
        version: reason for version, reason in result
    }


def add_yanked_attribute_per_version(
    project_page: model.ProjectDetail,
    yanked_versions: dict[str, str],
) -> model.ProjectDetail:
    if not yanked_versions:
        return project_page

    files = []
    for file in project_page.files:
        try:
            version = packaging.extract_package_version(
                filename=file.filename,
                project_name=canonicalize_name(project_page.name),
            )
        except ValueError:
            version = "unknown"
        reason = yanked_versions.get(version)
        if (not file.yanked) and (reason is not None):
            if reason == '':
                yanked: typing.Union[bool, str] = True
            else:
                yanked = html.escape(reason)
            file = replace(file, yanked=yanked)
        files.append(file)
    project_page = replace(project_page, files=tuple(files))
    return project_page


def add_yanked_attribute_per_file(
    project_page: model.ProjectDetail,
    yanked_files: dict[str, str],
) -> model.ProjectDetail:
    files = []
    for file in project_page.files:
        reason = yanked_files.get(file.filename)
        if (not file.yanked) and (reason is not None):
            if reason == '':
                yanked: bool | str = True
            else:
                yanked = html.escape(reason)
            file = replace(file, yanked=yanked)
        files.append(file)
    project_page = replace(project_page, files=tuple(files))
    return project_page


class YankRepository(RepositoryContainer):
    """A class that adds support for PEP-592 yank to a SimpleRepository.
    The project name, file name, and the yanking reason are stored in the
    yanked_versions table of the SQLite database passed to the constructor.
    Distributions that are already yanked will not be affected by this component.
    """
    def __init__(
        self,
        source: SimpleRepository,
        database: aiosqlite.Connection,
    ) -> None:
        self.yank_database = database
        # TODO: Use a synchronization mechanism instead.
        self._initialise_db = True
        super().__init__(source)

    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectDetail:
        project_page = await super().get_project_page(
            project_name,
            request_context=request_context,
        )

        await self._init_db()
        yanked_versions = await get_yanked_versions(project_name, self.yank_database)
        return add_yanked_attribute_per_version(
            project_page=project_page,
            yanked_versions=yanked_versions,
        )

    async def _init_db(self) -> None:
        if not self._initialise_db:
            return

        await self.yank_database.execute(
            "CREATE TABLE IF NOT EXISTS yanked_versions"
            "(project_name TEXT, version TEXT, reason TEXT,"
            " date TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ", CONSTRAINT pk PRIMARY KEY (project_name, version))",
        )
        self._initialise_db = False


class ConfigurableYankRepository(RepositoryContainer):
    """Yanks distributions according to the provided json configuration file.
    The file MUST contain a dictionary mapping project names to glob patterns
    and yank reasons. For a given project, all files matching the pattern will
    be yanked with the given reason.

    The configuration file must have the following structure:

        {
            "numpy": ["*.exe", "unsupported"],
            "tensorflow": ["*[!.whl]", "temporary"]
        }
    """
    def __init__(
        self,
        source: SimpleRepository,
        yank_config_file: pathlib.Path,
    ) -> None:
        self._yank_config: dict[str, tuple[str, str]] = self._load_config_json(yank_config_file)
        super().__init__(source)

    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectDetail:
        project_page = await super().get_project_page(
            project_name,
            request_context=request_context,
        )

        if value := self._yank_config.get(project_name):
            pattern, reason = value
            project_page = add_yanked_attribute_per_file(
                project_page=project_page,
                yanked_files={
                    file.filename: reason for file in project_page.files
                    if fnmatch.fnmatch(file.filename, pattern)
                },
            )

        return project_page

    def _load_config_json(self, json_file: pathlib.Path) -> dict[str, tuple[str, str]]:
        json_config = utils.load_config_json(json_file)

        config_dict: dict[str, tuple[str, str]] = {}
        for key, value in json_config.items():
            if (
                not isinstance(key, str) or
                not isinstance(value, list) or
                len(value) != 2 or
                not all(isinstance(elem, str) for elem in value)
            ):
                raise errors.InvalidConfigurationError(
                    f'Invalid yank configuration file. {str(json_file)} must'
                    ' contain a dictionary mapping a project name to a tuple'
                    ' containing a glob pattern and a yank reason.',
                )
            config_dict[canonicalize_name(key)] = (value[0], value[1])

        return config_dict
