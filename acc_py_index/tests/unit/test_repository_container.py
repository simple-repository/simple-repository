import pytest

from acc_py_index import errors
from acc_py_index.simple import model
from acc_py_index.simple.repositories import RepositoryContainer
from acc_py_index.tests.mock_repository import MockRepository


@pytest.mark.asyncio
async def test_get_project_page() -> None:
    repository = RepositoryContainer(
        MockRepository(
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
        MockRepository(
            project_list=model.ProjectList(
                meta=model.Meta("1.0"),
                projects={model.ProjectListElement("numpy")},
            ),
        ),
    )
    result = await repository.get_project_list()
    assert result.projects == {model.ProjectListElement("numpy")}
