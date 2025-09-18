# Copyright (C) 2025, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import dataclasses
import typing

from .. import model
from .._typing_compat import override
from . import core


class PrivateMetadataSettingRepository(core.RepositoryContainer):
    """
    A repository component that attaches private metadata to project pages.

    This component allows attaching arbitrary private metadata (keys starting with '_')
    to ProjectDetail objects. This is useful for adding repository-specific metadata
    such as source information, internal identifiers, or other implementation details.

    Example:
        >>> metadata = {'_repository_source': 'PyPI', '_internal_id': '12345'}
        >>> repo = PrivateMetadataSettingRepository(source_repo, metadata)
    """

    def __init__(
        self,
        source: core.SimpleRepository,
        project_metadata: typing.Mapping[str, typing.Any],
    ) -> None:
        super().__init__(source)
        self._project_metadata = model.PrivateMetadataMapping.from_any_mapping(
            project_metadata,
        )

    @override
    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.ProjectDetail:
        project_detail = await super().get_project_page(
            project_name,
            request_context=request_context,
        )

        # Merge existing private metadata with our metadata
        merged_metadata = project_detail.private_metadata | self._project_metadata

        return dataclasses.replace(
            project_detail,
            private_metadata=merged_metadata,
        )
