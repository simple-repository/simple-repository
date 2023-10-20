import pytest

from ... import model
from ...components.yanking import YankProvider, YankRepository
from .fake_repository import FakeRepository


class FakeYankProvider(YankProvider):
    async def yanked_versions(self, project_page: model.ProjectDetail) -> dict[str, str]:
        return {"1.0": "reason"}

    async def yanked_files(self, project_page: model.ProjectDetail) -> dict[str, str]:
        return {"project-1.0-any.whl": "reason"}


@pytest.fixture
def project_page() -> model.ProjectDetail:
    return model.ProjectDetail(
        model.Meta("1.0"), name="project", files=(
            model.File("project-1.0-any.whl", "url", {}),
            model.File("project-1.0.tar.gz", "url", {}),
            model.File("project-1.1.tar.gz", "url", {}),
        ),
    )


@pytest.fixture
def repository(project_page: model.ProjectDetail) -> YankRepository:
    source = FakeRepository(
        project_pages=[project_page],
    )
    provider = FakeYankProvider()

    return YankRepository(
        source=source,
        yank_provider=provider,
    )


def test_yank_per_version(repository: YankRepository, project_page: model.ProjectDetail) -> None:
    yanked_page = repository._add_yanked_attribute_per_version(
        project_page=project_page,
        yanked_versions={"1.0": "reason"},
    )
    assert yanked_page.files[0].yanked == "reason"
    assert yanked_page.files[1].yanked == "reason"
    assert yanked_page.files[2].yanked is None


def test_yank_per_file(repository: YankRepository, project_page: model.ProjectDetail) -> None:
    yanked_page = repository._add_yanked_attribute_per_file(
        project_page=project_page,
        yanked_files={"project-1.0-any.whl": "reason"},
    )
    assert yanked_page.files[0].yanked == "reason"
    assert yanked_page.files[1].yanked is None
    assert yanked_page.files[2].yanked is None


@pytest.mark.asyncio
async def test_get_project_page(repository: YankRepository) -> None:
    result = await repository.get_project_page("project")

    assert result.files[0].yanked == "reason"
    assert result.files[1].yanked == "reason"
    assert result.files[2].yanked is None
