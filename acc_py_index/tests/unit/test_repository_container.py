import pytest

from acc_py_index import errors
from acc_py_index.simple import model
from acc_py_index.simple.repositories import RepositoryContainer
from acc_py_index.tests.fake_repository import FakeRepository


@pytest.mark.asyncio
async def test_get_project_page() -> None:
    repository = RepositoryContainer(
        FakeRepository(
            project_pages=[
                model.ProjectDetail(model.Meta("1.0"), "numpy", files=[]),
            ],
        ),
    )
    result = await repository.get_project_page("numpy")
    assert result == model.ProjectDetail(model.Meta("1.0"), "numpy", files=[])
    with pytest.raises(errors.PackageNotFoundError):
        await repository.get_project_page("pandas")


@pytest.mark.asyncio
async def test_get_project_list() -> None:
    repository = RepositoryContainer(
        FakeRepository(
            project_list=model.ProjectList(
                meta=model.Meta("1.0"),
                projects={model.ProjectListElement("numpy")},
            ),
        ),
    )
    result = await repository.get_project_list()
    assert result.projects == {model.ProjectListElement("numpy")}


@pytest.mark.asyncio
async def test_get_resource() -> None:
    repository = RepositoryContainer(
        FakeRepository(
            resources={
                "numpy.whl": model.Resource(
                    "numpy_url", model.ResourceType.REMOTE_RESOURCE,
                ),
            },
        ),
    )
    result = await repository.get_resource("numpy", "numpy.whl")
    assert result.value == "numpy_url"
