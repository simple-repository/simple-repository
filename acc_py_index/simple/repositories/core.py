from typing import Protocol

from .. import model


class SimpleRepository(Protocol):
    async def get_project_page(
        self,
        project_name: str,
        request_context: model.RequestContext,
    ) -> model.ProjectDetail:
        ...

    async def get_project_list(
        self,
        request_context: model.RequestContext,
    ) -> model.ProjectList:
        ...

    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        request_context: model.RequestContext,
    ) -> model.Resource:
        ...


class RepositoryContainer(SimpleRepository):
    """A base class for components that enhance the functionality of a source
    `SimpleRepository`. If not overridden, the methods provided by this class
    will delegate to the corresponding methods of the source repository.
    """
    def __init__(self, source: SimpleRepository) -> None:
        self.source = source

    async def get_project_page(
        self,
        project_name: str,
        request_context: model.RequestContext,
    ) -> model.ProjectDetail:
        return await self.source.get_project_page(project_name, request_context)

    async def get_project_list(
        self,
        request_context: model.RequestContext,
    ) -> model.ProjectList:
        return await self.source.get_project_list(request_context)

    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        request_context: model.RequestContext,
    ) -> model.Resource:
        return await self.source.get_resource(project_name, resource_name, request_context)
