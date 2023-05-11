import fnmatch
import html
import logging
import pathlib
import re
import sqlite3

from packaging.utils import canonicalize_name

from .. import utils
from .model import ProjectDetail
from .repositories import RepositoryContainer, SimpleRepository

error_logger = logging.getLogger("gunicorn.error")


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
    for file in project_page.files:
        reason = yanked_versions.get(file.filename)
        if (not file.yanked) and (reason is not None):
            if reason == '':
                file.yanked = True
            else:
                file.yanked = html.escape(reason)
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
        self._yank_config_file = yank_config_file
        super().__init__(source)

    async def get_project_page(
        self,
        project_name: str,
    ) -> ProjectDetail:
        project_page = await super().get_project_page(project_name)
        config = utils.load_cached_json_config(self._yank_config_file)

        if not isinstance(config, dict):
            error_logger.error(
                "Yank configuration file must contain a dictionary.",
            )
            config = {}

        value = None
        for project in config:
            if canonicalize_name(project) == project_name:
                value = config.get(project)
                break

        if value:
            if (
                len(value) == 2
                and isinstance(value[0], str)
                and isinstance(value[1], str)
            ):
                pattern, reason = value
                regex = re.compile(fnmatch.translate(pattern))
                add_yanked_attribute(
                    project_page=project_page,
                    yanked_versions={
                        file.filename: reason for file in project_page.files
                        if regex.match(file.filename)
                    },
                )
            else:
                error_logger.error(
                    f"Invalid json structure for the project {project_name}",
                )

        return project_page
