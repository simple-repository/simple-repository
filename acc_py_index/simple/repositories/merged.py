import asyncio
from dataclasses import replace
import typing

from packaging.utils import canonicalize_name

from ... import errors
from ..model import ProjectDetail
from .priority_selected import PrioritySelectedProjectsRepository

if typing.TYPE_CHECKING:
    from .. import model


class MergedRepository(PrioritySelectedProjectsRepository):
    """
    Represents a merged view of all the given (unsorted) repositories

    NOTICE: The MergedRepository is combining the given repositories without
            giving exclusivity of a source of a specific package to any particular
            repositories. As a result, this implementation is vulnerable to
            dependency confusion. There are cases where this behaviour is desirable
            hence its existence, but if you are unsure of those reasons, consider
            using the :class:`PrioritySelectedProjectsRepository` instead.
    """
    async def get_project_page(self, project_name: str) -> ProjectDetail:
        """Retrieves a project page for the specified normalized project name
        by searching through the grouped list of sources and blending them together.

        Raises:
            NotNormalizedProjectName:
                The project name is not normalized.
        """
        if project_name != canonicalize_name(project_name):
            raise errors.NotNormalizedProjectName()

        result: typing.Optional[ProjectDetail] = None

        # Keep track of unique filenames for the merged files.
        files: typing.Dict[str, model.File] = {}

        project_pages: list[typing.Union[Exception, ProjectDetail]] = await asyncio.gather(
            *(
                source.get_project_page(project_name)
                for source in self.sources
            ),
            return_exceptions=True,
        )

        for project_page in project_pages:
            if isinstance(project_page, Exception):
                if not isinstance(project_page, errors.PackageNotFoundError):
                    raise project_page
            else:
                for file in project_page.files:
                    # Only add the file if the filename hasn't been seen before.
                    files.setdefault(file.filename, file)
                if result is None:
                    result = project_page

        if result is None:
            raise errors.PackageNotFoundError(
                package_name=project_name,
            )

        result = replace(result, files=tuple(files.values()))
        return result
