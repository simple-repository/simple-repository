import hashlib
import pathlib

from packaging.utils import canonicalize_name

from acc_py_index.simple.model import (
    File,
    Meta,
    ProjectDetail,
    ProjectList,
    ProjectListElement,
    Resource,
    ResourceType,
)

from .. import errors
from .repositories import SimpleRepository


def sha256sum(file_path: pathlib.Path) -> str:
    sha256 = hashlib.sha256()
    BUF_SIZE = 1024 * 64

    with open(file_path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()


class LocalRepository(SimpleRepository):
    """
    Creates a simple repository from a local directory.
    The directory must contain a subdirectory for each project,
    named as the normalized project name. Each subdirectory will
    contain the distributions associated with that project.
    Each file in a project page is mapped to a URL with the
    following structure: base_url / project_name / file_name.

    Note: It is not the responsibility of this class to map
    requests to a file url to a call to get_resource.
    """
    def __init__(
        self,
        index_path: pathlib.Path,
        base_url: str,
    ) -> None:
        if not index_path.is_dir():
            raise ValueError("index_path must be a directory")
        self._index_path = index_path
        self._base_url = base_url

    async def get_project_list(self) -> ProjectList:
        return ProjectList(
            meta=Meta("1.0"),
            projects={
                ProjectListElement(x.name)
                for x in self._index_path.iterdir() if x.is_dir()
            },
        )

    async def get_project_page(self, project_name: str) -> ProjectDetail:
        if project_name != canonicalize_name(project_name):
            raise errors.NotNormalizedProjectName()

        project_dir = (self._index_path / project_name).resolve()
        if not project_dir.is_dir():
            raise errors.PackageNotFoundError(project_name)

        return ProjectDetail(
            meta=Meta("1.0"),
            name=project_name,
            files=[
                File(
                    filename=file.name,
                    url=f"{self._base_url}/{project_name}/{file.name}",
                    hashes={
                        "sha256": sha256sum(file),
                    },
                ) for file in project_dir.iterdir() if file.is_file()
            ],
        )

    async def get_resource(self, project_name: str, resource_name: str) -> Resource:
        repository_uri = (self._index_path / project_name).resolve()
        resource_uri = (repository_uri / resource_name).resolve()

        if (
            not repository_uri.is_relative_to(self._index_path) or
            not resource_uri.is_relative_to(repository_uri)
        ):
            raise ValueError(
                f"{resource_uri} is not contained in {repository_uri}",
            )
        if not resource_uri.is_file():
            raise errors.ResourceUnavailable(resource_name)

        return Resource(
            value=str(resource_uri),
            type=ResourceType.LOCAL_RESOURCE,
        )
