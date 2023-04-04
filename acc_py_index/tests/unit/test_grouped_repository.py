from unittest import mock

import pytest

from acc_py_index import errors
from acc_py_index.simple.grouped_repository import GroupedRepository
from acc_py_index.simple.model import Meta, ProjectDetail, ProjectList, ProjectListElement

from ..mock_repository import MockRepository


@pytest.mark.asyncio
async def test_get_project_page() -> None:
    group_repository = GroupedRepository([
        MockRepository(),
        MockRepository(
            ProjectList(Meta('1.0'), {ProjectListElement("numpy")}),
            [ProjectDetail(Meta('1.0'), "numpy", files=[])],
        ),
        MockRepository(
            ProjectList(Meta('1.0'), {ProjectListElement("numpy")}),
            [ProjectDetail(Meta('WRONG'), "numpy", files=[])],
        ),
    ])

    resp = await group_repository.get_project_page(project_name="numpy")

    assert resp == ProjectDetail(Meta('1.0'), "numpy", files=[])


@pytest.mark.asyncio
async def test_get_project_page_failed() -> None:
    group_repository = GroupedRepository([
        MockRepository() for i in range(3)
    ])
    with pytest.raises(
        expected_exception=errors.PackageNotFoundError,
        match=r"Package 'numpy' was not found in the configured source",
    ):
        await group_repository.get_project_page("numpy")


@pytest.mark.asyncio
async def test_blended_get_project_list() -> None:
    meta = Meta(api_version="1.0")
    projects_elements = [
        {
            ProjectListElement("a_"),
            ProjectListElement("c"),
        }, {
            ProjectListElement("a-"),
            ProjectListElement("b"),
        }, {
            ProjectListElement("d"),
        },
    ]

    group_repository = GroupedRepository(
        sources=[
            MockRepository(ProjectList(Meta("1.0"), p)) for p in projects_elements
        ],
    )

    result = await group_repository.get_project_list()
    assert result == ProjectList(
        meta=meta,
        projects={
            ProjectListElement("a-"),
            ProjectListElement("b"),
            ProjectListElement("c"),
            ProjectListElement("d"),
        },
    )


@pytest.mark.asyncio
async def test_blended_get_project_list_failed() -> None:
    repo = GroupedRepository(
        sources=[
            mock.AsyncMock() for i in range(3)
        ],
    )
    assert isinstance(repo.sources[2], mock.Mock)
    repo.sources[2].get_project_list.side_effect = errors.SourceRepositoryUnavailable
    with pytest.raises(errors.SourceRepositoryUnavailable):
        await repo.get_project_list()


def test_group_repository_failed_init() -> None:
    with pytest.raises(ValueError):
        GroupedRepository([])


@pytest.mark.asyncio
async def test_not_normalized_package() -> None:
    group_repository = GroupedRepository([
        MockRepository() for i in range(3)
    ])
    with pytest.raises(errors.NotNormalizedProjectName):
        await group_repository.get_project_page("non_normalized")
