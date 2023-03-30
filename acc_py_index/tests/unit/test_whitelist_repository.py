import pathlib
from unittest import mock

import pytest

from acc_py_index.simple.aggregated_repositories import WhitelistRepository, get_special_cases


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


def test_get_special_cases() -> None:
    special_cases_json = '{"special_cases": ["case1", "case2", "case3"]}'
    m = mock.mock_open(read_data=special_cases_json)
    with mock.patch.object(pathlib.Path, "open", m):
        special_cases = get_special_cases(pathlib.Path('special_cases.json'))

        assert len(special_cases) == 3
        assert special_cases[0] == 'case1'
        assert special_cases[1] == 'case2'
        assert special_cases[2] == 'case3'
