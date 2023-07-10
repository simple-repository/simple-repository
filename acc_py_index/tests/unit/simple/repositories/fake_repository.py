from typing import Optional

from acc_py_index import errors
from acc_py_index.simple.model import Meta, ProjectDetail, ProjectList, Resource
from acc_py_index.simple.repositories.core import SimpleRepository


class FakeRepository(SimpleRepository):
    def __init__(
        self,
        project_list: ProjectList = ProjectList(Meta('1.0'), frozenset()),
        project_pages: Optional[list[ProjectDetail]] = None,
        resources: Optional[dict[str, Resource]] = None,
    ) -> None:
        self.project_list = project_list
        if project_pages:
            self.project_pages = {
                project.name: project for project in project_pages
            }
        else:
            self.project_pages = {}
        self.resources = resources or {}

    async def get_project_page(self, project_name: str) -> ProjectDetail:
        if project_name in self.project_pages:
            return self.project_pages[project_name]
        raise errors.PackageNotFoundError(project_name)

    async def get_project_list(self) -> ProjectList:
        return self.project_list

    async def get_resource(self, project_name: str, resource_name: str) -> Resource:
        if resource := self.resources.get(resource_name):
            return resource
        raise errors.ResourceUnavailable(resource_name)
