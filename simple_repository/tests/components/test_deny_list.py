import pytest

from ... import errors, model
from ...components.deny_list import DenyListRepository
from .fake_repository import FakeRepository


@pytest.fixture
def source_repository() -> FakeRepository:
    return FakeRepository(
        project_list=model.ProjectList(
            meta=model.Meta("1.0"),
            projects=frozenset([
                model.ProjectListElement("project1"),
                model.ProjectListElement("project2"),
                model.ProjectListElement("project3"),
            ]),
        ),
        project_pages=[
            model.ProjectDetail(
                meta=model.Meta("1.0"),
                name="project1",
                files=(),
            ),
            model.ProjectDetail(
                meta=model.Meta("1.0"),
                name="project2",
                files=(),
            ),
            model.ProjectDetail(
                meta=model.Meta("1.0"),
                name="project3",
                files=(),
            ),
        ],
        resources={
            "project1-1.0.tar.gz": model.HttpResource("content1"),
            "project2-1.0.tar.gz": model.HttpResource("content2"),
            "project3-1.0.tar.gz": model.HttpResource("content3"),
        },
    )


@pytest.fixture
def repository(source_repository: FakeRepository) -> DenyListRepository:
    return DenyListRepository(
        source=source_repository,
        deny_list=("project3"),
    )


@pytest.mark.asyncio
async def test__get_project_list(repository: DenyListRepository) -> None:
    project_list = await repository.get_project_list()
    assert project_list.projects == frozenset([
        model.ProjectListElement("project1"),
        model.ProjectListElement("project2"),
    ])


@pytest.mark.asyncio
async def test__get_project_page__not_deny_listed(
    repository: DenyListRepository,
    source_repository: FakeRepository,
) -> None:
    project_page = await repository.get_project_page("project1")
    assert project_page == source_repository.project_pages["project1"]


@pytest.mark.asyncio
async def test__get_project_page__deny_listed(repository: DenyListRepository) -> None:
    with pytest.raises(errors.PackageNotFoundError):
        await repository.get_project_page("project3")


@pytest.mark.asyncio
async def test__get_resource__not_deny_listed(repository: DenyListRepository) -> None:
    resource = await repository.get_resource("project1", "project1-1.0.tar.gz")
    assert isinstance(resource, model.HttpResource)
    assert resource.url == "content1"


@pytest.mark.asyncio
async def test__get_resource__deny_listed(repository: DenyListRepository) -> None:
    with pytest.raises(errors.ResourceUnavailable):
        await repository.get_resource("project3", "project3-1.0.tar.gz")
