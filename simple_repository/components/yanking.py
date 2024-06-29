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

from .. import errors, model
from .. import packaging as _packaging
from .. import utils
from .._typing_compat import override
from .core import RepositoryContainer, SimpleRepository


class YankProvider(typing.Protocol):
    async def yanked_versions(self, project_page: model.ProjectDetail) -> dict[str, str]:
        ...

    async def yanked_files(self, project_page: model.ProjectDetail) -> dict[str, str]:
        ...


class SqliteYankProvider(YankProvider):
    def __init__(self, database: aiosqlite.Connection) -> None:
        # TODO: Use a synchronization mechanism instead.
        self._initialise_db = True
        self._database = database

    async def _init_db(self) -> None:
        if not self._initialise_db:
            return

        await self._database.execute(
            "CREATE TABLE IF NOT EXISTS yanked_versions"
            "(project_name TEXT, version TEXT, reason TEXT,"
            " date TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ", CONSTRAINT pk PRIMARY KEY (project_name, version))",
        )
        await self._database.execute(
            "CREATE TABLE IF NOT EXISTS yanked_releases"
            "(project_name TEXT, file_name TEXT, reason TEXT,"
            " date TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ", CONSTRAINT pk PRIMARY KEY (project_name, file_name))",
        )
        self._initialise_db = False

    async def yanked_versions(self, project_page: model.ProjectDetail) -> dict[str, str]:
        await self._init_db()

        query = "SELECT version, reason FROM yanked_versions WHERE project_name = :project_name"
        async with self._database.execute(query, {"project_name": project_page.name}) as cur:
            result = await cur.fetchall()
        return {
            version: reason for version, reason in result
        }

    async def yanked_files(self, project_page: model.ProjectDetail) -> dict[str, str]:
        await self._init_db()

        query = "SELECT file_name, reason FROM yanked_releases WHERE project_name = :project_name"
        async with self._database.execute(query, {"project_name": project_page.name}) as cur:
            result = await cur.fetchall()
        return {
            filename: reason for filename, reason in result
        }


class GlobYankProvider(YankProvider):
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
        yank_config_file: pathlib.Path,
    ) -> None:
        self._yank_config: dict[str, tuple[str, str]] = self._load_config_json(yank_config_file)

    async def yanked_versions(self, project_page: model.ProjectDetail) -> dict[str, str]:
        # TODO: Manage yanked_versions in this component
        return {}

    async def yanked_files(self, project_page: model.ProjectDetail) -> dict[str, str]:
        yanked_files = {}
        if value := self._yank_config.get(project_page.name):
            pattern, reason = value
            yanked_files = {
                file.filename: reason for file in project_page.files
                if fnmatch.fnmatch(file.filename, pattern)
            }

        return yanked_files

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


def update_yanked_attribute(file: model.File, reason: str) -> model.File:
    if reason == '':
        yanked: bool | str = True
    else:
        yanked = html.escape(reason)
    return replace(file, yanked=yanked)


class YankRepository(RepositoryContainer):
    """
    A class that adds support for PEP-592 yank to a SimpleRepository.

    The information related to which version or file of a project are yanked
    comes from a provider that specialized the protocol YankProvider.
    """
    def __init__(
        self,
        source: SimpleRepository,
        yank_provider: YankProvider,
    ) -> None:
        self._yank_provider = yank_provider
        super().__init__(source)

    @override
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

        yanked_versions = await self._yank_provider.yanked_versions(project_page)
        yanked_files = await self._yank_provider.yanked_files(project_page)

        if yanked_versions or yanked_files:
            project_page = self._add_yanked_attribute(
                project_page=project_page,
                yanked_files=yanked_files,
                yanked_versions=yanked_versions,
            )

        return project_page

    def _add_yanked_attribute(
        self,
        project_page: model.ProjectDetail,
        yanked_versions: dict[str, str],
        yanked_files: dict[str, str],
    ) -> model.ProjectDetail:
        files = []
        for file in project_page.files:
            if file.yanked:
                # Skip already yanked files
                pass
            elif reason := yanked_files.get(file.filename):
                file = update_yanked_attribute(file, reason)
            else:
                try:
                    version = _packaging.extract_package_version(
                        filename=file.filename,
                        project_name=canonicalize_name(project_page.name),
                    )
                except ValueError:
                    pass
                else:
                    if reason := yanked_versions.get(version):
                        file = update_yanked_attribute(file, reason)

            files.append(file)

        return replace(project_page, files=tuple(files))
