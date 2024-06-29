from dataclasses import replace

from simple_repository.model import ProjectDetail, ProjectList, RequestContext, Resource

from .. import errors, model
from .._typing_compat import override
from .core import RepositoryContainer, SimpleRepository


class DenyListRepository(RepositoryContainer):
    def __init__(self, source: SimpleRepository, deny_list: tuple[str, ...]) -> None:
        super().__init__(source)
        self._deny_list = deny_list

    @override
    async def get_project_list(
        self,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> ProjectList:
        project_list = await super().get_project_list(request_context=request_context)
        projects = frozenset(
            elem for elem in project_list.projects if elem.normalized_name not in self._deny_list
        )
        return replace(project_list, projects=projects)

    @override
    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: RequestContext = model.RequestContext.DEFAULT,
    ) -> ProjectDetail:
        if project_name in self._deny_list:
            raise errors.PackageNotFoundError(project_name)
        return await super().get_project_page(project_name, request_context=request_context)

    @override
    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: RequestContext = model.RequestContext.DEFAULT,
    ) -> Resource:
        if project_name in self._deny_list:
            raise errors.ResourceUnavailable(resource_name)
        return await super().get_resource(
            project_name, resource_name, request_context=request_context,
        )
