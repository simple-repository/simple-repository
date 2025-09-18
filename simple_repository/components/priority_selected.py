# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import asyncio
import typing

import packaging.utils
import packaging.version

from .. import errors, model
from .._typing_compat import override
from . import core


class PrioritySelectedProjectsRepository(core.SimpleRepository):
    """Group together multiple repositories, using a first-seen policy

    When the list of all projects is requested, returns the union of all
    projects in all sources. When a specific project is requested, returns
    the first source which has the project, and does not include project
    information from any other source. Note that the project name being
    requested is normalized, to absolutely prevent against dependency
    confusion attacks from sources later in the sequence.
    """

    def __init__(self, sources: typing.Sequence[core.SimpleRepository]) -> None:
        if len(sources) < 2:
            raise ValueError(
                "A priority selected repository must have two or more "
                "source repositories",
            )
        self.sources = sources

    @override
    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.ProjectDetail:
        """Retrieves a project page for the specified normalized project name
        by searching through the grouped list of sources in a first seen policy.
        """
        for source in self.sources:
            try:
                project_page = await source.get_project_page(
                    project_name,
                    request_context=request_context,
                )
            except errors.PackageNotFoundError:
                continue
            return project_page

        raise errors.PackageNotFoundError(
            package_name=project_name,
        )

    @override
    async def get_project_list(
        self,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.ProjectList:
        """Retrieves a combined list of projects from all the sources."""
        results: typing.List[
            typing.Union[model.ProjectList, BaseException]
        ] = await asyncio.gather(
            *(
                source.get_project_list(request_context=request_context)
                for source in self.sources
            ),
            return_exceptions=True,
        )

        project_lists = [
            item for item in results if isinstance(item, model.ProjectList)
        ]

        if len(project_lists) != len(self.sources):
            # TODO: Use an exception group to raise
            # multiple exceptions together.
            any_exception = next(
                item for item in results if isinstance(item, BaseException)
            )
            raise any_exception

        projects = set().union(
            *(index.projects for index in project_lists),
        )

        # Downgrade the API version to the lowest available, as it will not be
        # possible to calculate the missing files to perform a version upgrade.
        api_version = min(
            packaging.version.Version(project.meta.api_version)
            for project in project_lists
        )
        return model.ProjectList(
            meta=model.Meta(str(api_version)),
            projects=frozenset(
                model.ProjectListElement(
                    name=packaging.utils.canonicalize_name(p.name),
                )
                for p in projects
            ),
        )

    @override
    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.Resource:
        """Retrieves a resource from the first source that has the project.

        This follows the same first-seen project policy as get_project_page.
        Repositories are expected to raise PackageNotFoundError when they don't
        have the project, and ResourceUnavailable when they have the project but
        not the resource.
        """
        for source in self.sources:
            try:
                return await source.get_resource(
                    project_name,
                    resource_name,
                    request_context=request_context,
                )
            except errors.PackageNotFoundError:
                # This source doesn't have the project, try next source
                continue
            except errors.ResourceUnavailable:
                # This source has the project but not the specific resource
                # Following first-seen policy, we don't check other sources
                raise

        # No source has the project
        raise errors.PackageNotFoundError(project_name)
