import pathlib

import pytest

from acc_py_index import errors
from acc_py_index.simple.model import Meta, ProjectDetail, ProjectList, ProjectListElement
from acc_py_index.simple.white_list_repository import WhitelistRepository

from ..mock_repository import MockRepository


@pytest.mark.asyncio
async def test_special_get_project_page(tmp_path: pathlib.PosixPath) -> None:
    special_case_file = tmp_path / "special_cases.json"
    special_case_file.write_text('{"numpy": "url", "pandas": "url"}')

    repo = WhitelistRepository(
        source=MockRepository(
            project_pages=[
                ProjectDetail(Meta("1.0"), "numpy", files=[]),
                ProjectDetail(Meta("1.0"), "tensorflow", files=[]),
            ],
        ),
        special_case_file=special_case_file,
    )

    resp = await repo.get_project_page("numpy")
    assert resp == ProjectDetail(Meta("1.0"), "numpy", files=[])

    with pytest.raises(errors.PackageNotFoundError, match="package"):
        await repo.get_project_page("package")

    with pytest.raises(errors.PackageNotFoundError, match="tensorflow"):
        await repo.get_project_page("tensorflow")


@pytest.mark.asyncio
async def test_get_project_list(tmp_path: pathlib.PosixPath) -> None:
    special_case_file = tmp_path / "special_cases.json"
    special_case_file.write_text('{"numpy": "url", "pandas": "url"}')

    repo = WhitelistRepository(
        source=MockRepository(),
        special_case_file=special_case_file,
    )

    res = await repo.get_project_list()

    assert res == ProjectList(
        meta=Meta("1.0"),
        projects={ProjectListElement("numpy"), ProjectListElement("pandas")},
    )


@pytest.mark.asyncio
async def test_not_normalized_package() -> None:
    repo = WhitelistRepository(
        source=MockRepository(),
        special_case_file=pathlib.Path("./test.json"),
    )
    with pytest.raises(errors.NotNormalizedProjectName):
        await repo.get_project_page("non_normalized")


@pytest.mark.asyncio
async def test_get_resources(tmp_path: pathlib.PosixPath) -> None:
    special_case_file = tmp_path / "special_cases.json"
    special_case_file.write_text('{"numpy": "url", "pandas": "url"}')

    repo = WhitelistRepository(
        source=MockRepository(resources={"gunicorn-0.7.whl": "gunicorn_url", "numpy-0.7.whl": "numpy_url"}),
        special_case_file=special_case_file,
    )

    with pytest.raises(
        errors.ResourceUnavailable,
        match="gunicorn-0.7.whl",
    ):
        await repo.get_resource("gunicorn", "gunicorn-0.7.whl")

    with pytest.raises(
        errors.ResourceUnavailable,
        match="pandas.whl",
    ):
        await repo.get_resource("pandas", "pandas.whl")

    result = await repo.get_resource("numpy", "numpy-0.7.whl")
    assert result.url == "numpy_url"
