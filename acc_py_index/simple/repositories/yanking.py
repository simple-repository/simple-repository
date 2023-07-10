from dataclasses import replace
import fnmatch
import html
import pathlib
import sqlite3
import typing

from packaging.utils import canonicalize_name

from ... import errors, utils
from ..model import ProjectDetail
from .core import RepositoryContainer, SimpleRepository


def get_yanked_releases(project_name: str, database: sqlite3.Connection) -> dict[str, str]:
    query = "SELECT file_name, reason FROM yanked_releases WHERE project_name = :project_name"
    curr = database.cursor()
    result = curr.execute(query, {"project_name": project_name}).fetchall()
    return {
        file_name: record for file_name, record in result
    }


def add_yanked_attribute(
    project_page: ProjectDetail,
    yanked_versions: dict[str, str],
) -> ProjectDetail:
    files = []
    for file in project_page.files:
        reason = yanked_versions.get(file.filename)
        if (not file.yanked) and (reason is not None):
            if reason == '':
                yanked: typing.Union[bool, str] = True
            else:
                yanked = html.escape(reason)
            file = replace(file, yanked=yanked)
        files.append(file)
    project_page = replace(project_page, files=tuple(files))
    return project_page


class YankRepository(RepositoryContainer):
    """A class that adds support for PEP-592 yank to a SimpleRepository.
    The project name, file name, and the yanking reason are stored in the
    yanked_releases table of the SQLite database passed to the constructor.
    Distributions that are already yanked will not be affected by this component.
    """
    def __init__(
        self,
        source: SimpleRepository,
        database: sqlite3.Connection,
    ) -> None:
        curr = database.cursor()
        curr.execute(
            "CREATE TABLE IF NOT EXISTS yanked_releases"
            "(project_name TEXT, file_name TEXT, reason TEXT"
            ", CONSTRAINT pk PRIMARY KEY (project_name, file_name))",
        )
        self.yank_database = database
        super().__init__(source)

    async def get_project_page(
        self,
        project_name: str,
    ) -> ProjectDetail:
        project_page = await super().get_project_page(project_name)

        if yanked_versions := get_yanked_releases(project_name, self.yank_database):
            return add_yanked_attribute(
                project_page=project_page,
                yanked_versions=yanked_versions,
            )
        return project_page


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
    ) -> ProjectDetail:
        project_page = await super().get_project_page(project_name)

        if value := self._yank_config.get(project_name):
            pattern, reason = value
            project_page = add_yanked_attribute(
                project_page=project_page,
                yanked_versions={
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
