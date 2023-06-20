from pathlib import Path

import pytest

from acc_py_index import errors
from acc_py_index.simple import model
from acc_py_index.simple.repositories.local import LocalRepository, sha256sum


@pytest.fixture
def simple_dir(tmp_path: Path) -> Path:
    for project in ("numpy", "tensorflow", "pandas", ".not_normalized"):
        (tmp_path / project).mkdir()
    for file in ("numpy-1.0-any.whl", "numpy-1.1.tar.gz"):
        (tmp_path / "numpy" / file).write_text("content")
    (tmp_path / ".not_normalized" / "unreachable_resource").touch()
    return tmp_path


@pytest.mark.asyncio
async def test_get_project_list(simple_dir: Path) -> None:
    repo = LocalRepository(
        index_path=simple_dir,
    )
    project_list = await repo.get_project_list()

    assert project_list == model.ProjectList(
        meta=model.Meta("1.0"),
        projects={
            model.ProjectListElement("numpy"),
            model.ProjectListElement("tensorflow"),
            model.ProjectListElement("pandas"),
        },
    )


@pytest.mark.asyncio
async def test_get_resource(simple_dir: Path) -> None:
    repo = LocalRepository(
        index_path=simple_dir,
    )
    resource = await repo.get_resource("numpy", "numpy-1.0-any.whl")

    assert resource == model.Resource(
        value=str(simple_dir / "numpy" / "numpy-1.0-any.whl"),
        type=model.ResourceType.LOCAL_RESOURCE,
    )


@pytest.mark.parametrize(
    ("project, resource"), [
        ("numpy", "numpy-2.0.tar.gz"),
        ("seaborn", "seaborn-1.0.tar.gz"),
    ],
)
@pytest.mark.asyncio
async def test_get_resource__unavailable(
    simple_dir: Path,
    project: str,
    resource: str,
) -> None:
    repo = LocalRepository(
        index_path=simple_dir,
    )
    with pytest.raises(
        errors.ResourceUnavailable,
        match=f"Resource '{resource}' was not found in the configured source",
    ):
        await repo.get_resource(project, resource)


@pytest.mark.parametrize(
    ("project, resource"), [
        ("numpy", "../../../etc/password"),
        ("tensorflow", "../numpy/numpy-1.0.tar.gz"),
    ],
)
@pytest.mark.asyncio
async def test_get_resource__path_traversal(
    simple_dir: Path,
    project: str,
    resource: str,
) -> None:
    repo = LocalRepository(
        index_path=simple_dir,
    )

    with pytest.raises(
        ValueError,
        match=f"{(simple_dir / project /resource).resolve()} is not contained in {repo._index_path / project}",
    ):
        await repo.get_resource(project, resource)


@pytest.mark.asyncio
async def test_get_resource__not_normalized(
    simple_dir: Path,
) -> None:
    repo = LocalRepository(
        index_path=simple_dir,
    )

    with pytest.raises(
        errors.NotNormalizedProjectName,
    ):
        await repo.get_resource(".not_normalized", "unreachable_resource")


@pytest.mark.asyncio
async def test_get_project_page(simple_dir: Path) -> None:
    repo = LocalRepository(
        index_path=simple_dir,
    )

    project_details = await repo.get_project_page("numpy")
    assert project_details == model.ProjectDetail(
        meta=model.Meta("1.0"),
        name="numpy",
        files=[
            model.File(
                filename='numpy-1.0-any.whl',
                url="file://" + str(simple_dir / 'numpy/numpy-1.0-any.whl'),
                # On the fly hashes currently disabled for local repository.
                hashes={
                    # "sha256": sha256sum(simple_dir / "numpy" / "numpy-1.0-any.whl"),
                },
            ),
            model.File(
                filename='numpy-1.1.tar.gz',
                url="file://" + str(simple_dir / 'numpy/numpy-1.1.tar.gz'),
                hashes={
                    # "sha256": sha256sum(simple_dir / "numpy" / "numpy-1.1.tar.gz"),
                },
            ),
        ],
    )


@pytest.mark.asyncio
async def test_get_project_page__not_found(simple_dir: Path) -> None:
    repo = LocalRepository(
        index_path=simple_dir,
    )

    with pytest.raises(
        errors.PackageNotFoundError,
        match="seaborn",
    ):
        await repo.get_project_page("seaborn")


def test_sha256sum(tmp_path: Path) -> None:
    file = tmp_path / "my_file.txt"
    file.write_text("ciao\n")

    assert sha256sum(file) == "6f0378f21a495f5c13247317d158e9d51da45a5bf68fc2f366e450deafdc8302"
