# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import asyncio
import typing

from packaging.version import Version

from .. import errors, model
from .priority_selected import PrioritySelectedProjectsRepository


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
    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectDetail:
        """Retrieves a project page for the specified normalized project name
        by searching through the grouped list of sources and blending them together.
        """
        # Keep track of unique filenames for the merged files.
        files: typing.Dict[str, model.File] = {}

        results: list[Exception | model.ProjectDetail] = await asyncio.gather(
            *(
                source.get_project_page(
                    project_name,
                    request_context=request_context,
                )
                for source in self.sources
            ),
            return_exceptions=True,
        )

        project_pages: list[model.ProjectDetail] = []
        for result in results:
            if isinstance(result, Exception):
                if not isinstance(result, errors.PackageNotFoundError):
                    raise result
            else:
                for file in result.files:
                    # Only add the file if the filename hasn't been seen before.
                    files.setdefault(file.filename, file)
                project_pages.append(result)

        if not project_pages:
            raise errors.PackageNotFoundError(
                package_name=project_name,
            )

        # Downgrade the API version to the lowest available, as it will not be
        # possible to calculate the missing files to perform a version upgrade.
        api_version = str(
            min((
                Version(result.meta.api_version) for result in project_pages
            )),
        )

        return model.ProjectDetail(
            meta=model.Meta(api_version),
            name=project_pages[0].name,
            files=tuple(files.values()),
        )
