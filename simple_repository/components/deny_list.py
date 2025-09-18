# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

from dataclasses import replace
import typing

from .. import errors, model
from .._typing_compat import override
from . import core


class DenyListRepository(core.RepositoryContainer):
    def __init__(
        self,
        source: core.SimpleRepository,
        deny_list: typing.Tuple[str, ...],
    ) -> None:
        super().__init__(source)
        self._deny_list = deny_list

    @override
    async def get_project_list(
        self,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.ProjectList:
        project_list = await super().get_project_list(request_context=request_context)
        projects = frozenset(
            elem
            for elem in project_list.projects
            if elem.normalized_name not in self._deny_list
        )
        return replace(project_list, projects=projects)

    @override
    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.ProjectDetail:
        if project_name in self._deny_list:
            raise errors.PackageNotFoundError(project_name)
        return await super().get_project_page(
            project_name,
            request_context=request_context,
        )

    @override
    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.Resource:
        if project_name in self._deny_list:
            raise errors.ResourceUnavailable(resource_name)
        return await super().get_resource(
            project_name,
            resource_name,
            request_context=request_context,
        )
