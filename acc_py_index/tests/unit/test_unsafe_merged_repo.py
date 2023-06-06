import pytest

from acc_py_index import errors
from acc_py_index.simple.grouped_repository import UnsafeMergedRepository
from acc_py_index.simple.model import File, Meta, ProjectDetail

from ..mock_repository import MockRepository


@pytest.mark.asyncio
async def test_get_project_page() -> None:
    repo = UnsafeMergedRepository(
        [
            MockRepository(),
            MockRepository(
                project_pages=[
                    ProjectDetail(
                        Meta('1.0'),
                        "numpy",
                        files=[
                            File("numpy-1.1.whl", "url1", {}),
                            File("numpy-1.2.whl", "url1", {}),
                        ],
                    ),
                ],
            ),
            MockRepository(
                project_pages=[
                    ProjectDetail(
                        Meta('1.0'),
                        "numpy",
                        files=[
                            File("numpy-1.1.whl", "url2", {}),
                            File("numpy-1.3.whl", "url2", {}),
                        ],
                    ),
                ],
            ),
        ],
    )

    resp = await repo.get_project_page(project_name="numpy")

    assert resp == ProjectDetail(
        Meta('1.0'),
        "numpy",
        files=[
            File("numpy-1.1.whl", "url1", {}),
            File("numpy-1.2.whl", "url1", {}),
            File("numpy-1.3.whl", "url2", {}),
        ],
    )


@pytest.mark.asyncio
async def test_get_project_page_failed() -> None:
    repo = UnsafeMergedRepository([
        MockRepository() for _ in range(3)
    ])

    with pytest.raises(
        errors.PackageNotFoundError,
        match="Package 'numpy' was not found in the configured source",
    ):
        await repo.get_project_page("numpy")


@pytest.mark.asyncio
async def test_not_normalized_package() -> None:
    repo = UnsafeMergedRepository([
        MockRepository() for _ in range(3)
    ])
    with pytest.raises(errors.NotNormalizedProjectName):
        await repo.get_project_page("non_normalized")
