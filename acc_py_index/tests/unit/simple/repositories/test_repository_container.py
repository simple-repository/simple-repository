
import pytest

from acc_py_index.simple import errors, model
from acc_py_index.simple.repositories.core import RepositoryContainer

from .fake_repository import FakeRepository


@pytest.mark.asyncio
async def test_get_project_page() -> None:
    repository = RepositoryContainer(
        FakeRepository(
            project_pages=[
                model.ProjectDetail(model.Meta("1.0"), "numpy", files=()),
            ],
        ),
    )
    result = await repository.get_project_page("numpy", model.RequestContext(repository))
    assert result == model.ProjectDetail(model.Meta("1.0"), "numpy", files=())
    with pytest.raises(errors.PackageNotFoundError):
        await repository.get_project_page("pandas", model.RequestContext(repository))


@pytest.mark.asyncio
async def test_get_project_list() -> None:
    repository = RepositoryContainer(
        FakeRepository(
            project_list=model.ProjectList(
                meta=model.Meta("1.0"),
                projects=frozenset([model.ProjectListElement("numpy")]),
            ),
        ),
    )
    result = await repository.get_project_list(model.RequestContext(repository))
    assert result.projects == frozenset([model.ProjectListElement("numpy")])


@pytest.mark.asyncio
async def test_get_resource() -> None:
    repository = RepositoryContainer(
        FakeRepository(
            resources={
                "numpy.whl": model.HttpResource("numpy_url"),
            },
        ),
    )
    result = await repository.get_resource("numpy", "numpy.whl", model.RequestContext(repository))
    assert isinstance(result, model.HttpResource)
    assert result.url == "numpy_url"
