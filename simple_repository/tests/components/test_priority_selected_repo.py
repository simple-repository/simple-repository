# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import pytest

from ... import errors, model
from ...components.priority_selected import PrioritySelectedProjectsRepository
from .fake_repository import FakeRepository
from .mock_compat import AsyncMock


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "version",
    [
        "1.0",
        "1.1",
    ],
)
async def test_get_project_page(version: str) -> None:
    group_repository = PrioritySelectedProjectsRepository(
        [
            FakeRepository(),
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        model.Meta(version),
                        "numpy",
                        files=(
                            model.File("1", "1", {}, size=1),
                            model.File("2", "2", {}, size=1),
                        ),
                    ),
                ],
            ),
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        model.Meta("1.0"),
                        "numpy",
                        files=(model.File("3", "3", {}),),
                    ),
                ],
            ),
        ],
    )

    resp = await group_repository.get_project_page(
        project_name="numpy",
    )

    assert resp == model.ProjectDetail(
        model.Meta(version),
        "numpy",
        files=(
            model.File("1", "1", {}, size=1),
            model.File("2", "2", {}, size=1),
        ),
    )


@pytest.mark.asyncio
async def test_get_project_page_failed() -> None:
    group_repository = PrioritySelectedProjectsRepository(
        [FakeRepository() for _ in range(3)],
    )
    with pytest.raises(
        expected_exception=errors.PackageNotFoundError,
        match=r"Package 'numpy' was not found in the configured source",
    ):
        await group_repository.get_project_page("numpy")


@pytest.mark.asyncio
async def test_blended_get_project_list() -> None:
    meta = model.Meta(api_version="1.0")
    projects_elements = [
        frozenset(
            [
                model.ProjectListElement("a_"),
                model.ProjectListElement("c"),
            ],
        ),
        frozenset(
            [
                model.ProjectListElement("a-"),
                model.ProjectListElement("b"),
            ],
        ),
        frozenset(
            [
                model.ProjectListElement("d"),
            ],
        ),
    ]

    group_repository = PrioritySelectedProjectsRepository(
        sources=[
            FakeRepository(
                model.ProjectList(model.Meta("1.0"), p),
            )
            for p in projects_elements
        ],
    )

    result = await group_repository.get_project_list()
    # We expect only normalized results, and no duplicates.
    assert result == model.ProjectList(
        meta=meta,
        projects=frozenset(
            [
                model.ProjectListElement("a-"),
                model.ProjectListElement("b"),
                model.ProjectListElement("c"),
                model.ProjectListElement("d"),
            ],
        ),
    )


@pytest.mark.asyncio
async def test_blended_get_project_list_failed() -> None:
    repo = PrioritySelectedProjectsRepository(
        sources=[
            AsyncMock(),
            AsyncMock(),
            AsyncMock(),
        ],
    )
    assert isinstance(repo.sources[2], AsyncMock)
    repo.sources[2].get_project_list.side_effect = errors.SourceRepositoryUnavailable
    with pytest.raises(errors.SourceRepositoryUnavailable):
        await repo.get_project_list()


@pytest.mark.asyncio
async def test_blended_get_project_page_failed() -> None:
    repo = PrioritySelectedProjectsRepository(
        sources=[
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        meta=model.Meta("1.0"),
                        name="numpy",
                        files=(),
                    ),
                ],
            ),
            AsyncMock(),
        ],
    )
    assert isinstance(repo.sources[1], AsyncMock)
    repo.sources[1].get_project_list.side_effect = Exception

    res = await repo.get_project_page("numpy")

    assert res == model.ProjectDetail(
        model.Meta("1.0"),
        name="numpy",
        files=(),
    )


def test_group_repository_failed_init() -> None:
    with pytest.raises(ValueError):
        PrioritySelectedProjectsRepository([])
    with pytest.raises(ValueError):
        PrioritySelectedProjectsRepository([FakeRepository()])


@pytest.mark.asyncio
async def test_get_resource() -> None:
    group_repository = PrioritySelectedProjectsRepository(
        [
            FakeRepository(),
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        meta=model.Meta("1.0"),
                        name="numpy",
                        files=(),
                    ),
                ],
                resources={
                    "numpy.whl": model.HttpResource("url"),
                },
            ),
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        meta=model.Meta("1.0"),
                        name="numpy",
                        files=(),
                    ),
                ],
                resources={
                    "numpy.whl": model.HttpResource("undesirable"),
                },
            ),
        ],
    )

    resp = await group_repository.get_resource("numpy", "numpy.whl")
    assert resp == model.HttpResource("url")


@pytest.mark.asyncio
async def test_get_resource__resource_exists_but_not_package() -> None:
    group_repository = PrioritySelectedProjectsRepository(
        [
            FakeRepository(
                resources={
                    "numpy.whl": model.HttpResource("url"),
                },
            ),
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        meta=model.Meta("1.0"),
                        name="numpy",
                        files=(),
                    ),
                ],
            ),
        ],
    )

    with pytest.raises(errors.ResourceUnavailable):
        await group_repository.get_resource("numpy", "numpy.whl")


@pytest.mark.asyncio
async def test_get_resource__subresource_exists_in_lower_priority() -> None:
    group_repository = PrioritySelectedProjectsRepository(
        [
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        meta=model.Meta("1.0"),
                        name="numpy",
                        files=(),
                    ),
                ],
                resources={
                    "numpy.whl": model.HttpResource("url"),
                },
            ),
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        meta=model.Meta("1.0"),
                        name="numpy",
                        files=(),
                    ),
                ],
                resources={
                    "numpy.whl": model.HttpResource("undesirable1"),
                    "numpy.whl.metadata": model.HttpResource("undesirable2"),
                },
            ),
        ],
    )

    with pytest.raises(errors.ResourceUnavailable):
        await group_repository.get_resource("numpy", "numpy.whl.metadata")


@pytest.mark.asyncio
async def test_get_resource__first_repo_has_project_but_missing_resource() -> None:
    group_repository = PrioritySelectedProjectsRepository(
        [
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        meta=model.Meta("1.0"),
                        name="numpy",
                        files=(),
                    ),
                ],
                # Note: has project page but NO resources
            ),
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        meta=model.Meta("1.0"),
                        name="numpy",
                        files=(),
                    ),
                ],
                resources={
                    "numpy.whl": model.HttpResource("should_not_be_used"),
                },
            ),
        ],
    )

    # Should raise ResourceUnavailable from first repo, not fall back to second
    with pytest.raises(errors.ResourceUnavailable):
        await group_repository.get_resource("numpy", "numpy.whl")


@pytest.mark.asyncio
async def test_get_resource__no_package() -> None:
    group_repository = PrioritySelectedProjectsRepository(
        [FakeRepository() for _ in range(3)],
    )

    with pytest.raises(errors.PackageNotFoundError, match="numpy"):
        await group_repository.get_resource("numpy", "numpy.whl")
