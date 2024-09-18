from __future__ import annotations

from ... import errors, model
from ...components import core


class FakeRepository(core.SimpleRepository):

    def __init__(
        self,
        project_list: model.ProjectList = model.ProjectList(model.Meta('1.0'), frozenset()),
        project_pages: list[model.ProjectDetail] | None = None,
        resources: dict[str, model.Resource] | None = None,
    ) -> None:
        self.project_list = project_list
        if project_pages:
            self.project_pages = {
                project.name: project for project in project_pages
            }
        else:
            self.project_pages = {}
        self.resources = resources or {}

    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectDetail:
        if project_name in self.project_pages:
            return self.project_pages[project_name]
        raise errors.PackageNotFoundError(project_name)

    async def get_project_list(
        self,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectList:
        return self.project_list

    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.Resource:
        resource = self.resources.get(resource_name)
        if resource:
            return resource
        raise errors.ResourceUnavailable(resource_name)
