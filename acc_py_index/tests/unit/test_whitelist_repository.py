import pathlib
from unittest import mock

import pytest

from acc_py_index import errors
from acc_py_index.simple.model import Meta, ProjectDetail, ProjectList, ProjectListElement
from acc_py_index.simple.white_list_repository import WhitelistRepository, get_special_cases

from ..mock_repository import MockRepository


@pytest.mark.asyncio
async def test_special_get_project_page() -> None:
    repo = WhitelistRepository(
        source=MockRepository(
            project_list=ProjectList(Meta("1.0"), {ProjectListElement("numpy")}),
            project_pages=[ProjectDetail(Meta("1.0"), "numpy", files=[])],
        ),
        special_case_file=pathlib.Path("./test.json"),
    )

    special_cases = ["jinja2", "numpy"]

    with mock.patch("acc_py_index.simple.white_list_repository.get_special_cases", return_value=special_cases):
        resp = await repo.get_project_page("numpy")
        assert resp == ProjectDetail(Meta("1.0"), "numpy", files=[])

    with mock.patch("acc_py_index.simple.white_list_repository.get_special_cases", return_value=special_cases):
        with pytest.raises(errors.PackageNotFoundError):
            await repo.get_project_page("package")


@pytest.mark.asyncio
async def test_get_project_list() -> None:
    repo = WhitelistRepository(
        source=MockRepository(),
        special_case_file=pathlib.Path("./test.json"),
    )

    special_cases = ["p1", "p2"]

    with mock.patch("acc_py_index.simple.white_list_repository.get_special_cases", return_value=special_cases):
        res = await repo.get_project_list()

    assert res == ProjectList(
        meta=Meta("1.0"),
        projects={ProjectListElement("p1"), ProjectListElement("p2")},
    )


def test_get_special_cases() -> None:
    special_cases_json = '{"c1": "", "c2": "", "c3": ""}'
    m = mock.mock_open(read_data=special_cases_json)
    with mock.patch.object(pathlib.Path, "open", m):
        special_cases = get_special_cases(pathlib.Path('special_cases.json'))

        for special_case, expected in zip(special_cases, ["c1", "c2", "c3"]):
            assert special_case == expected


@pytest.mark.asyncio
async def test_not_normalized_package() -> None:
    repo = WhitelistRepository(
        source=MockRepository(),
        special_case_file=pathlib.Path("./test.json"),
    )
    with pytest.raises(errors.NotNormalizedProjectName):
        await repo.get_project_page("non_normalized")
