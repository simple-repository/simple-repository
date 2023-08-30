import pytest

from acc_py_index import errors
from acc_py_index.simple import model
from acc_py_index.simple.repositories.merged import MergedRepository

from .fake_repository import FakeRepository


@pytest.mark.asyncio
async def test_get_project_page() -> None:
    repo = MergedRepository(
        [
            FakeRepository(),
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        model.Meta('1.1'),
                        "numpy",
                        files=(
                            model.File("numpy-1.1.whl", "url1", {}, size=1),
                            model.File("numpy-1.2.whl", "url1", {}, size=1),
                        ),
                    ),
                ],
            ),
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        model.Meta('1.0'),
                        "numpy",
                        files=(
                            model.File("numpy-1.1.whl", "url2", {}),
                            model.File("numpy-1.3.whl", "url2", {}),
                        ),
                    ),
                ],
            ),
        ],
    )

    resp = await repo.get_project_page("numpy", model.RequestContext(repo))

    assert resp == model.ProjectDetail(
        model.Meta('1.0'),
        "numpy",
        files=(
            model.File("numpy-1.1.whl", "url1", {}, size=1),
            model.File("numpy-1.2.whl", "url1", {}, size=1),
            model.File("numpy-1.3.whl", "url2", {}),
        ),
    )


@pytest.mark.asyncio
async def test_get_project_page_failed() -> None:
    repo = MergedRepository([
        FakeRepository() for _ in range(3)
    ])

    with pytest.raises(
        errors.PackageNotFoundError,
        match="Package 'numpy' was not found in the configured source",
    ):
        await repo.get_project_page("numpy", model.RequestContext(repo))
