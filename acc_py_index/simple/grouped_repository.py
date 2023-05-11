import asyncio
from collections.abc import Sequence

from packaging.utils import canonicalize_name

from .. import errors
from .model import ProjectDetail, ProjectList, ProjectListElement, Resource
from .repositories import SimpleRepository


class GroupedRepository(SimpleRepository):
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
            raise ValueError("A grouped repository must have two or more source repositories")
        self.sources = sources

    async def get_project_page(self, project_name: str) -> ProjectDetail:
        """Retrieves a project page for the specified normalized project name
        by searching through the grouped list of sources in a first seen policy.
        Raises NotNormalizedProjectName is the project page is not normalized.
        """
        if project_name != canonicalize_name(project_name):
            raise errors.NotNormalizedProjectName()

        for source in self.sources:
            try:
                project_page = await source.get_project_page(project_name)
            except errors.PackageNotFoundError:
                continue
            return project_page

        raise errors.PackageNotFoundError(
            package_name=project_name,
        )

    async def get_project_list(self) -> ProjectList:
        """Retrieves a combined list of projects from all the sources."""
        project_lists: list[ProjectList] = await asyncio.gather(
            *(
                source.get_project_list()
                for source in self.sources
            ),
            return_exceptions=True,
        )
        for project_list in project_lists:
            if isinstance(project_list, Exception):
                # TODO: Use an exception group to raise
                # multiple exceptions together.
                raise project_list

        if not all(
            project.meta.api_version == project_lists[0].meta.api_version
            for project in project_lists
        ):
            # TODO: Properly handle different API versions.
            raise errors.UnsupportedSerialization()

        projects = set().union(
            *[
                index.projects for index in project_lists
            ],
        )

        return ProjectList(
            meta=project_lists[0].meta,
            projects={
                ProjectListElement(
                    name=canonicalize_name(p.name),
                ) for p in projects
            },
        )

    async def get_resource(self, project_name: str, resource_name: str) -> Resource:
        for source in self.sources:
            try:
                resource = await source.get_resource(project_name, resource_name)
            except errors.ResourceUnavailable:
                pass
            else:
                return resource
        raise errors.ResourceUnavailable(resource_name)
