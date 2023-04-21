import html
import sqlite3

from .model import ProjectDetail
from .repositories import RepositoryContainer, SimpleRepository


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
