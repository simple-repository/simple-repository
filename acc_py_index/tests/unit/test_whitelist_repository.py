import pathlib
from unittest import mock

import pytest

from acc_py_index import errors
from acc_py_index.simple.aggregated_repositories import WhitelistRepository, get_special_cases
from acc_py_index.simple.model import Meta, ProjectList, ProjectListElement


@pytest.mark.asyncio
async def test_special_get_project_page() -> None:
    repo = WhitelistRepository(
        default_source=mock.AsyncMock(),
        special_source=mock.AsyncMock(),
        special_case_file=pathlib.Path("./test.json"),
    )

    assert isinstance(repo.special_source, mock.Mock)
    assert isinstance(repo.default_source, mock.Mock)

    special_cases = ["p1", "p2", "numpy", "p3"]

    with mock.patch("acc_py_index.simple.aggregated_repositories.get_special_cases", return_value=special_cases) as m:
        await repo.get_project_page("numpy")
        repo.special_source.get_project_page.assert_awaited_once_with("numpy")
        m.assert_called_once_with(pathlib.Path("./test.json"))

    with mock.patch("acc_py_index.simple.aggregated_repositories.get_special_cases", return_value=special_cases) as m:
        await repo.get_project_page("package")
        repo.default_source.get_project_page.assert_awaited_once_with("package")
        m.assert_called_once_with(pathlib.Path("./test.json"))


@pytest.mark.asyncio
async def test_get_project_list() -> None:
    repo = WhitelistRepository(
        default_source=mock.AsyncMock(),
        special_source=mock.AsyncMock(),
        special_case_file=pathlib.Path("./test.json"),
    )

    assert isinstance(repo.special_source, mock.Mock)
    assert isinstance(repo.default_source, mock.Mock)

    special_cases = ["p1"]
    repo.default_source.get_project_list.return_value = ProjectList(
        meta=Meta("1.0"),
        projects={ProjectListElement("p2")},
    )

    with mock.patch("acc_py_index.simple.aggregated_repositories.get_special_cases", return_value=special_cases):
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
        default_source=mock.AsyncMock(),
        special_source=mock.AsyncMock(),
        special_case_file=pathlib.Path("./test.json"),
    )
    with pytest.raises(errors.NotNormalizedProjectName):
        await repo.get_project_page("non_normalized")
