# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import typing

import pytest

from ... import errors, model
from ...components.allow_list import AllowListRepository

if typing.TYPE_CHECKING:
    from .fake_repository import FakeRepository


@pytest.fixture
def repository(source_repository: FakeRepository) -> AllowListRepository:
    return AllowListRepository(
        source=source_repository,
        allow_list=("project1", "project2"),
    )


@pytest.mark.asyncio
async def test__get_project_list(repository: AllowListRepository) -> None:
    project_list = await repository.get_project_list()
    assert project_list.projects == frozenset(
        [
            model.ProjectListElement("project1"),
            model.ProjectListElement("project2"),
        ],
    )


@pytest.mark.asyncio
async def test__get_project_page__allow_listed(
    repository: AllowListRepository,
    source_repository: FakeRepository,
) -> None:
    project_page = await repository.get_project_page("project1")
    assert project_page == source_repository.project_pages["project1"]


@pytest.mark.asyncio
async def test__get_project_page__not_allow_listed(
    repository: AllowListRepository,
) -> None:
    with pytest.raises(errors.PackageNotFoundError):
        await repository.get_project_page("project3")


@pytest.mark.asyncio
async def test__get_resource__allow_listed(repository: AllowListRepository) -> None:
    resource = await repository.get_resource("project1", "project1-1.0.tar.gz")
    assert isinstance(resource, model.HttpResource)
    assert resource.url == "content1"


@pytest.mark.asyncio
async def test__get_resource__not_allow_listed(repository: AllowListRepository) -> None:
    with pytest.raises(errors.ResourceUnavailable):
        await repository.get_resource("project3", "project3-1.0.tar.gz")
