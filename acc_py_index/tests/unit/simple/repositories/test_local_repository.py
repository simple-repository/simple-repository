from datetime import datetime
import os
from pathlib import Path

import pytest

from acc_py_index import errors
from acc_py_index.simple import model
from acc_py_index.simple.repositories.local import LocalRepository


@pytest.fixture
def simple_dir(tmp_path: Path) -> Path:
    for project in ("numpy", "tensorflow", "pandas", ".not_normalized"):
        (tmp_path / project).mkdir()
    for file in ("numpy-1.0-any.whl", "numpy-1.1.tar.gz"):
        (tmp_path / "numpy" / file).write_text("content")
    (tmp_path / ".not_normalized" / "unreachable_resource").touch()
    return tmp_path


@pytest.fixture
def repository(simple_dir: Path) -> LocalRepository:
    return LocalRepository(simple_dir)


@pytest.mark.asyncio
async def test_get_project_list(simple_dir: Path) -> None:
    repo = LocalRepository(
        index_path=simple_dir,
    )
    context = model.RequestContext(repo)

    project_list = await repo.get_project_list(context)

    assert project_list == model.ProjectList(
        meta=model.Meta("1.0"),
        projects=frozenset([
            model.ProjectListElement("numpy"),
            model.ProjectListElement("tensorflow"),
            model.ProjectListElement("pandas"),
        ]),
    )


@pytest.mark.asyncio
async def test_get_resource(simple_dir: Path) -> None:
    repo = LocalRepository(
        index_path=simple_dir,
    )
    context = model.RequestContext(repo)
    resource = await repo.get_resource("numpy", "numpy-1.0-any.whl", context)

    assert resource == model.LocalResource(
        path=simple_dir / "numpy" / "numpy-1.0-any.whl",
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
    context = model.RequestContext(repo)

    with pytest.raises(
        errors.ResourceUnavailable,
        match=f"Resource '{resource}' was not found in the configured source",
    ):
        await repo.get_resource(project, resource, context)


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
    context = model.RequestContext(repo)

    with pytest.raises(
        ValueError,
        match=f"{(simple_dir / project /resource).resolve()} is not contained in {repo._index_path / project}",
    ):
        await repo.get_resource(project, resource, context)


@pytest.mark.asyncio
async def test_get_project_page(simple_dir: Path) -> None:
    repo = LocalRepository(
        index_path=simple_dir,
    )
    context = model.RequestContext(repo)

    project_details = await repo.get_project_page("numpy", context)
    assert project_details == model.ProjectDetail(
        meta=model.Meta("1.1"),
        name="numpy",
        files=(
            model.File(
                filename='numpy-1.0-any.whl',
                url="file://" + str(simple_dir / 'numpy/numpy-1.0-any.whl'),
                # On the fly hashes currently disabled for local repository.
                hashes={
                    # "sha256": sha256sum(simple_dir / "numpy" / "numpy-1.0-any.whl"),
                },
                upload_time=datetime.utcfromtimestamp(
                        os.path.getctime(simple_dir / "numpy" / "numpy-1.0-any.whl"),
                ),
                size=os.stat(simple_dir / "numpy" / "numpy-1.0-any.whl").st_size,
            ),
            model.File(
                filename='numpy-1.1.tar.gz',
                url="file://" + str(simple_dir / 'numpy/numpy-1.1.tar.gz'),
                hashes={
                    # "sha256": sha256sum(simple_dir / "numpy" / "numpy-1.1.tar.gz"),
                },
                upload_time=datetime.utcfromtimestamp(
                        os.path.getctime(simple_dir / "numpy" / "numpy-1.1.tar.gz"),
                ),
                size=os.stat(simple_dir / "numpy" / "numpy-1.1.tar.gz").st_size,
            ),
        ),
    )


@pytest.mark.asyncio
async def test_get_project_page__not_found(simple_dir: Path) -> None:
    repo = LocalRepository(
        index_path=simple_dir,
    )
    context = model.RequestContext(repo)

    with pytest.raises(
        errors.PackageNotFoundError,
        match="seaborn",
    ):
        await repo.get_project_page("seaborn", context)
