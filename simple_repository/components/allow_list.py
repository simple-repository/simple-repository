from dataclasses import replace

from simple_repository.model import ProjectDetail, ProjectList, RequestContext, Resource

from .. import errors, model
from .core import RepositoryContainer, SimpleRepository


class AllowListRepository(RepositoryContainer):
    def __init__(self, source: SimpleRepository, allow_list: tuple[str, ...]) -> None:
        super().__init__(source)
        self._allow_list = allow_list

    async def get_project_list(
        self,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> ProjectList:
        project_list = await super().get_project_list(request_context=request_context)
        projects = frozenset([
            elem for elem in project_list.projects if elem.normalized_name in self._allow_list
        ])
        return replace(project_list, projects=projects)

    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: RequestContext = model.RequestContext.DEFAULT,
    ) -> ProjectDetail:
        if project_name not in self._allow_list:
            raise errors.PackageNotFoundError(project_name)
        return await super().get_project_page(project_name, request_context=request_context)

    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: RequestContext = model.RequestContext.DEFAULT,
    ) -> Resource:
        if project_name not in self._allow_list:
            raise errors.ResourceUnavailable(resource_name)
        return await super().get_resource(
            project_name, resource_name, request_context=request_context,
        )
