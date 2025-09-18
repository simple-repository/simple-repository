# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import typing

from ... import errors, model
from ...components import core


class FakeRepository(core.SimpleRepository):
    def __init__(
        self,
        project_list: model.ProjectList = model.ProjectList(
            model.Meta("1.0"),
            frozenset(),
        ),
        project_pages: typing.Optional[typing.List[model.ProjectDetail]] = None,
        resources: typing.Optional[typing.Dict[str, model.Resource]] = None,
    ) -> None:
        self.project_list = project_list
        if project_pages:
            self.project_pages = {project.name: project for project in project_pages}
        else:
            self.project_pages = {}
        self.resources = resources or {}

    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.ProjectDetail:
        if project_name in self.project_pages:
            return self.project_pages[project_name]
        raise errors.PackageNotFoundError(project_name)

    async def get_project_list(
        self,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.ProjectList:
        return self.project_list

    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.Resource:
        # Check if we have this project first
        try:
            await self.get_project_page(project_name, request_context=request_context)
        except errors.PackageNotFoundError:
            raise

        # Look for the specific resource
        resource = self.resources.get(resource_name)
        if resource:
            return resource
        raise errors.ResourceUnavailable(resource_name)
