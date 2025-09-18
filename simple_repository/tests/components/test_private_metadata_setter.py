# Copyright (C) 2025, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import typing

import pytest

from ... import model
from ...components.private_metadata_setter import PrivateMetadataSettingRepository

if typing.TYPE_CHECKING:
    from .fake_repository import FakeRepository


@pytest.fixture
def private_meta_repo(
    source_repository: FakeRepository,
) -> PrivateMetadataSettingRepository:
    return PrivateMetadataSettingRepository(
        source=source_repository,
        project_metadata={"_repository_source": "PyPI", "_internal_id": "12345"},
    )


@pytest.mark.asyncio
async def test__get_project_page__adds_metadata(
    private_meta_repo: PrivateMetadataSettingRepository,
    source_repository: FakeRepository,
) -> None:
    project_page = await private_meta_repo.get_project_page("project1")

    assert project_page.name == "project1"
    assert project_page.private_metadata["_repository_source"] == "PyPI"
    assert project_page.private_metadata["_internal_id"] == "12345"


@pytest.mark.asyncio
async def test__get_project_page__merges_existing_metadata(
    source_repository: FakeRepository,
) -> None:
    # Create a source repository with existing private metadata
    source_repository.project_pages["project1"] = model.ProjectDetail(
        meta=model.Meta("1.0"),
        name="project1",
        files=(),
        private_metadata=model.PrivateMetadataMapping.from_any_mapping(
            {
                "_existing_key": "existing_value",
            },
        ),
    )

    repository = PrivateMetadataSettingRepository(
        source=source_repository,
        project_metadata={"_repository_source": "PyPI", "_internal_id": "12345"},
    )

    project_page = await repository.get_project_page("project1")

    assert project_page.private_metadata["_existing_key"] == "existing_value"
    assert project_page.private_metadata["_repository_source"] == "PyPI"
    assert project_page.private_metadata["_internal_id"] == "12345"


@pytest.mark.asyncio
async def test__get_project_page__overwrites_conflicting_metadata(
    source_repository: FakeRepository,
) -> None:
    # Create a source repository with conflicting private metadata
    source_repository.project_pages["project1"] = model.ProjectDetail(
        meta=model.Meta("1.0"),
        name="project1",
        files=(),
        private_metadata=model.PrivateMetadataMapping.from_any_mapping(
            {
                "_repository_source": "internal",
            },
        ),
    )

    repository = PrivateMetadataSettingRepository(
        source=source_repository,
        project_metadata={"_repository_source": "PyPI"},
    )

    project_page = await repository.get_project_page("project1")

    # Our metadata should overwrite the existing one
    assert project_page.private_metadata["_repository_source"] == "PyPI"


@pytest.mark.asyncio
async def test__get_project_list__delegates_to_source(
    private_meta_repo: PrivateMetadataSettingRepository,
    source_repository: FakeRepository,
) -> None:
    project_list = await private_meta_repo.get_project_list()

    # Should be the same as the source repository
    assert project_list == source_repository.project_list


@pytest.mark.asyncio
async def test__get_resource__delegates_to_source(
    private_meta_repo: PrivateMetadataSettingRepository,
) -> None:
    resource = await private_meta_repo.get_resource("project1", "project1-1.0.tar.gz")

    assert isinstance(resource, model.HttpResource)
    assert resource.url == "content1"


def test__init__validates_private_metadata_keys(
    source_repository: FakeRepository,
) -> None:
    # Valid keys (starting with underscore)
    repository = PrivateMetadataSettingRepository(
        source=source_repository,
        project_metadata={"_valid_key": "value"},
    )
    assert repository._project_metadata["_valid_key"] == "value"

    # Invalid keys should raise ValueError
    with pytest.raises(ValueError, match="invalid for private metadata"):
        PrivateMetadataSettingRepository(
            source=source_repository,
            project_metadata={"invalid_key": "value"},  # Missing underscore prefix
        )
