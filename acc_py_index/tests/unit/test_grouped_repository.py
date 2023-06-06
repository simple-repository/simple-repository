from unittest import mock

import pytest

from acc_py_index import errors
from acc_py_index.simple import model
from acc_py_index.simple.grouped_repository import GroupedRepository

from ..fake_repository import FakeRepository


@pytest.mark.asyncio
async def test_get_project_page() -> None:
    group_repository = GroupedRepository([
        FakeRepository(),
        FakeRepository(
            project_pages=[
                model.ProjectDetail(
                    model.Meta('1.0'),
                    "numpy",
                    files=[model.File("1", "1", {}), model.File("2", "2", {})],
                ),
            ],
        ),
        FakeRepository(
            project_pages=[
                model.ProjectDetail(
                    model.Meta('1.0'),
                    "numpy",
                    files=[model.File("3", "3", {})],
                ),
            ],
        ),
    ])

    resp = await group_repository.get_project_page(project_name="numpy")

    assert resp == model.ProjectDetail(
        model.Meta('1.0'),
        "numpy",
        files=[
            model.File("1", "1", {}), model.File("2", "2", {}),
        ],
    )


@pytest.mark.asyncio
async def test_get_project_page_failed() -> None:
    group_repository = GroupedRepository([
        FakeRepository() for _ in range(3)
    ])
    with pytest.raises(
        expected_exception=errors.PackageNotFoundError,
        match=r"Package 'numpy' was not found in the configured source",
    ):
        await group_repository.get_project_page("numpy")


@pytest.mark.asyncio
async def test_blended_get_project_list() -> None:
    meta = model.Meta(api_version="1.0")
    projects_elements = [
        {
            model.ProjectListElement("a_"),
            model.ProjectListElement("c"),
        }, {
            model.ProjectListElement("a-"),
            model.ProjectListElement("b"),
        }, {
            model.ProjectListElement("d"),
        },
    ]

    group_repository = GroupedRepository(
        sources=[
            FakeRepository(
                model.ProjectList(model.Meta("1.0"), p),
            ) for p in projects_elements
        ],
    )

    result = await group_repository.get_project_list()
    # We expect only normalized results, and no duplicates.
    assert result == model.ProjectList(
        meta=meta,
        projects={
            model.ProjectListElement("a-"),
            model.ProjectListElement("b"),
            model.ProjectListElement("c"),
            model.ProjectListElement("d"),
        },
    )


@pytest.mark.asyncio
async def test_blended_get_project_list_failed() -> None:
    repo = GroupedRepository(
        sources=[
            mock.AsyncMock() for _ in range(3)
        ],
    )
    assert isinstance(repo.sources[2], mock.Mock)
    repo.sources[2].get_project_list.side_effect = errors.SourceRepositoryUnavailable
    with pytest.raises(errors.SourceRepositoryUnavailable):
        await repo.get_project_list()


@pytest.mark.asyncio
async def test_blended_get_project_page_failed() -> None:
    repo = GroupedRepository(
        sources=[
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        meta=model.Meta("1.0"),
                        name="numpy",
                        files=[],
                    ),
                ],
            ),
            mock.AsyncMock(),
        ],
    )
    assert isinstance(repo.sources[1], mock.Mock)
    repo.sources[1].get_project_list.side_effect = Exception

    res = await repo.get_project_page("numpy")

    assert res == model.ProjectDetail(
        model.Meta("1.0"), name="numpy", files=[],
    )


def test_group_repository_failed_init() -> None:
    with pytest.raises(ValueError):
        GroupedRepository([])
    with pytest.raises(ValueError):
        GroupedRepository([FakeRepository()])


@pytest.mark.asyncio
async def test_not_normalized_package() -> None:
    group_repository = GroupedRepository([
        FakeRepository() for _ in range(3)
    ])
    with pytest.raises(errors.NotNormalizedProjectName):
        await group_repository.get_project_page("non_normalized")


@pytest.mark.asyncio
async def test_get_resource() -> None:
    group_repository = GroupedRepository([
        FakeRepository(),
        FakeRepository(
            resources={
                "numpy.whl": model.Resource(
                    "url", model.ResourceType.REMOTE_RESOURCE,
                ),
            },
        ),
        FakeRepository(
            resources={
                "numpy.whl": model.Resource(
                    "wrog", model.ResourceType.REMOTE_RESOURCE,
                ),
            },
        ),
    ])

    resp = await group_repository.get_resource("numpy", "numpy.whl")
    assert resp == model.Resource(
        value="url",
        type=model.ResourceType.REMOTE_RESOURCE,
    )


@pytest.mark.asyncio
async def test_get_resource_failed() -> None:
    group_repository = GroupedRepository([
        FakeRepository() for _ in range(3)
    ])

    with pytest.raises(errors.ResourceUnavailable, match="numpy.whl"):
        await group_repository.get_resource("numpy", "numpy.whl")
