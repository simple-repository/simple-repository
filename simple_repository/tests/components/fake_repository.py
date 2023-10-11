# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from typing import Optional

from ... import errors, model
from ...components.core import SimpleRepository


class FakeRepository(SimpleRepository):
    def __init__(
        self,
        project_list: model.ProjectList = model.ProjectList(model.Meta('1.0'), frozenset()),
        project_pages: Optional[list[model.ProjectDetail]] = None,
        resources: Optional[dict[str, model.Resource]] = None,
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
        if resource := self.resources.get(resource_name):
            return resource
        raise errors.ResourceUnavailable(resource_name)
