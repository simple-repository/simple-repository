# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import asyncio
from collections.abc import Sequence

from packaging.utils import canonicalize_name
from packaging.version import Version

from .. import errors, model
from .core import SimpleRepository


class PrioritySelectedProjectsRepository(SimpleRepository):
    """Group together multiple repositories, using a first-seen policy

    When the list of all projects is requested, returns the union of all
    projects in all sources. When a specific project is requested, returns
    the first source which has the project, and does not include project
    information from any other source. Note that the project name being
    requested is normalized, to absolutely prevent against dependency
    confusion attacks from sources later in the sequence.
    """
    def __init__(self, sources: Sequence[SimpleRepository]) -> None:
        if len(sources) < 2:
            raise ValueError(
                "A priority selected repository must have two or more "
                "source repositories",
            )
        self.sources = sources

    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
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

    async def get_project_list(
        self,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectList:
        """Retrieves a combined list of projects from all the sources."""
        project_lists: list[model.ProjectList] = await asyncio.gather(
            *(
                source.get_project_list(request_context=request_context)
                for source in self.sources
            ),
            return_exceptions=True,
        )
        for project_list in project_lists:
            if isinstance(project_list, Exception):
                # TODO: Use an exception group to raise
                # multiple exceptions together.
                raise project_list

        projects = set().union(
            *[
                index.projects for index in project_lists
            ],
        )

        # Downgrade the API version to the lowest available, as it will not be
        # possible to calculate the missing files to perform a version upgrade.
        api_version = min(Version(project.meta.api_version) for project in project_lists)
        return model.ProjectList(
            meta=model.Meta(str(api_version)),
            projects=frozenset(
                model.ProjectListElement(
                    name=canonicalize_name(p.name),
                ) for p in projects
            ),
        )

    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.Resource:
        for source in self.sources:
            try:
                resource = await source.get_resource(
                    project_name,
                    resource_name,
                    request_context=request_context,
                )
            except errors.ResourceUnavailable:
                pass
            else:
                return resource
        raise errors.ResourceUnavailable(resource_name)
