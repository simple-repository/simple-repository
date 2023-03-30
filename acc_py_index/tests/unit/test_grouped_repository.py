from unittest import mock

import pytest

from acc_py_index import errors
from acc_py_index.simple import aggregated_repositories
from acc_py_index.simple.aggregated_repositories import GroupedRepository
from acc_py_index.simple.model import Meta, ProjectList, ProjectListElement


def test_blend_project_lists() -> None:
    meta = Meta(api_version="1.0")
    projects_elements = [
        {
            ProjectListElement("a"),
            ProjectListElement("c"),
        }, {
            ProjectListElement("a"),
            ProjectListElement("b"),
        }, {
            ProjectListElement("d"),
        },
    ]

    project_lists = [
        ProjectList(
            meta=meta,
            projects=projects,
        ) for projects in projects_elements
    ]
    blended_project = aggregated_repositories._blend_project_lists(project_lists)
    assert blended_project == ProjectList(
        meta=meta,
        projects={
            ProjectListElement("a"),
            ProjectListElement("b"),
            ProjectListElement("c"),
            ProjectListElement("d"),
        },
    )


@pytest.fixture
def group_repository() -> GroupedRepository:
    repo = GroupedRepository(
        sources=[
            mock.AsyncMock() for i in range(3)
        ],
    )
    return repo


@pytest.mark.asyncio
async def test_get_project_page(group_repository: GroupedRepository) -> None:
    assert isinstance(group_repository.sources[0], mock.Mock)
    assert isinstance(group_repository.sources[1], mock.Mock)
    assert isinstance(group_repository.sources[2], mock.Mock)

    group_repository.sources[0].get_project_page.side_effect = errors.PackageNotFoundError(package_name="numpy")

    await group_repository.get_project_page(project_name="numpy")

    group_repository.sources[0].get_project_page.assert_awaited_once_with("numpy")
    group_repository.sources[1].get_project_page.assert_awaited_once_with("numpy")
    group_repository.sources[2].get_project_page.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_project_page_failed(group_repository: GroupedRepository) -> None:
    assert isinstance(group_repository.sources[0], mock.Mock)
    assert isinstance(group_repository.sources[1], mock.Mock)
    assert isinstance(group_repository.sources[2], mock.Mock)

    group_repository.sources[0].get_project_page.side_effect = errors.PackageNotFoundError(package_name="numpy")
    group_repository.sources[1].get_project_page.side_effect = errors.PackageNotFoundError(package_name="numpy")
    group_repository.sources[2].get_project_page.side_effect = errors.PackageNotFoundError(package_name="numpy")

    with pytest.raises(
        expected_exception=errors.PackageNotFoundError,
        match=r"Package 'numpy' was not found in the configured source",
    ):
        await group_repository.get_project_page(project_name="numpy")

    group_repository.sources[0].get_project_page.assert_awaited_once_with("numpy")
    group_repository.sources[1].get_project_page.assert_awaited_once_with("numpy")
    group_repository.sources[2].get_project_page.assert_awaited_once_with("numpy")


@pytest.mark.asyncio
async def test_blended_get_project_list(group_repository: GroupedRepository) -> None:
    with mock.patch("acc_py_index.simple.aggregated_repositories._blend_project_lists") as m:
        await group_repository.get_project_list()
        m.assert_called_once()
        for source in group_repository.sources:
            assert isinstance(source, mock.Mock)
            source.get_project_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_blended_get_project_list_failed(group_repository: GroupedRepository) -> None:
    assert isinstance(group_repository.sources[0], mock.Mock)
    assert isinstance(group_repository.sources[1], mock.Mock)
    assert isinstance(group_repository.sources[2], mock.Mock)

    group_repository.sources[2].get_project_list.side_effect = errors.SourceRepositoryUnavailable
    with pytest.raises(errors.SourceRepositoryUnavailable):
        await group_repository.get_project_list()


def test_group_repository_failed_init() -> None:
    with pytest.raises(ValueError):
        GroupedRepository([])
