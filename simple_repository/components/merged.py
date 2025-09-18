# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import asyncio
import typing

import packaging.version

from .. import errors, model
from .._typing_compat import override
from . import priority_selected


class MergedRepository(priority_selected.PrioritySelectedProjectsRepository):
    """
    Represents a merged view of all the given (unsorted) repositories

    NOTICE: The MergedRepository is combining the given repositories without
            giving exclusivity of a source of a specific package to any particular
            repositories. As a result, this implementation is vulnerable to
            dependency confusion. There are cases where this behaviour is desirable
            hence its existence, but if you are unsure of those reasons, consider
            using the :class:`PrioritySelectedProjectsRepository` instead.
    """

    @override
    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.ProjectDetail:
        """Retrieves a project page for the specified normalized project name
        by searching through the grouped list of sources and blending them together.
        """
        # Keep track of unique filenames for the merged files.
        files: typing.Dict[str, model.File] = {}

        results: typing.List[
            typing.Union[
                BaseException,
                model.ProjectDetail,
            ]
        ] = await asyncio.gather(
            *(
                source.get_project_page(
                    project_name,
                    request_context=request_context,
                )
                for source in self.sources
            ),
            return_exceptions=True,
        )

        project_pages: typing.List[model.ProjectDetail] = []
        for result in results:
            if isinstance(result, BaseException):
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

        # If we only have one resulting project page, bring it through verbatim,
        # and avoid the cost of having to compute the common metadata.
        if len(project_pages) == 1:
            return project_pages[0]

        # Downgrade the API version to the lowest available, as it will not be
        # possible to calculate the missing files to perform a version upgrade.
        api_version = min(
            packaging.version.Version(result.meta.api_version)
            for result in project_pages
        )

        versions = None
        if api_version >= packaging.version.Version("1.1"):
            # All project pages are >=1.1, therefore they MUST all have
            # versions specified. We combine them together.
            all_versions: typing.List[typing.FrozenSet[str]] = typing.cast(
                typing.List[typing.FrozenSet[str]],
                [page.versions for page in project_pages],
            )
            versions = frozenset().union(*all_versions)

        # Merge private metadata from all project pages (first seen wins)
        merged_metadata: dict[str, typing.Any] = {}
        for page in reversed(project_pages):
            merged_metadata.update(page.private_metadata)

        return model.ProjectDetail(
            meta=model.Meta(str(api_version)),
            name=project_pages[0].name,
            files=tuple(files.values()),
            versions=versions,
            private_metadata=model.PrivateMetadataMapping.from_any_mapping(
                merged_metadata,
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
        """
        Retrieves a resource from any source that has it.
        """
        project_found = False
        for source in self.sources:
            try:
                return await source.get_resource(
                    project_name,
                    resource_name,
                    request_context=request_context,
                )
            except errors.PackageNotFoundError:
                # Try the next source
                continue
            except errors.ResourceUnavailable:
                project_found = True
                # Try the next source
                continue

        # No source has the resource
        if not project_found:
            raise errors.PackageNotFoundError(project_name)
        else:
            raise errors.ResourceUnavailable(resource_name)
