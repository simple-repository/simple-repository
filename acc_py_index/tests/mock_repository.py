from acc_py_index import errors
from acc_py_index.simple.model import Meta, ProjectDetail, ProjectList
from acc_py_index.simple.repositories import SimpleRepository


class MockRepository(SimpleRepository):
    def __init__(
        self,
        project_list: ProjectList = ProjectList(Meta('1.0'), set()),
        project_pages: list[ProjectDetail] = [],
    ) -> None:
        self.project_list = project_list
        self.project_pages = project_pages

    async def get_project_page(self, project_name: str) -> ProjectDetail:
        for p in self.project_pages:
            if p.name == project_name:
                return p
        raise errors.PackageNotFoundError(project_name)

    async def get_project_list(self) -> ProjectList:
        return self.project_list
