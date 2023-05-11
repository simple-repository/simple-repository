import pathlib
import typing

import pytest

from acc_py_index.simple import model
from acc_py_index.simple.yank_repository import ConfigurableYankRepository
from acc_py_index.tests.mock_repository import MockRepository


@pytest.fixture
def source() -> MockRepository:
    return MockRepository(
        project_pages=[
            model.ProjectDetail(
                model.Meta("1.0"),
                "numpy",
                [
                    model.File("numpy-1.0.whl", "url", {}),
                    model.File("numpy-1.0.tar.gz", "url", {}),
                ],
            ),
        ],
    )


@pytest.mark.asyncio
async def test_get_project_page(
    tmp_path: pathlib.PosixPath,
    source: MockRepository,
) -> None:
    file = tmp_path / "yank_config.json"
    file.write_text(
        data='{"numpy": ["*.whl", "bad"], "pandas": "*[!.whl]"}',
    )

    repo = ConfigurableYankRepository(
        source, file,
    )

    res = await repo.get_project_page("numpy")
    assert res.files[0].yanked == "bad"
    assert res.files[1].yanked is None


@pytest.mark.parametrize(
    "json_string", [
        "42", "true", '["a", "b"]', "null", '"ciao"',
    ],
)
@pytest.mark.asyncio
async def test_get_project_page_wrong_type(
    json_string: typing.Any,
    tmp_path: pathlib.PosixPath,
    source: MockRepository,
    caplog: pytest.LogCaptureFixture,
) -> None:
    file = tmp_path / "yank_config.json"
    file.write_text(
        data=json_string,
    )
    repo = ConfigurableYankRepository(
        source, file,
    )
    old_caplog_records = caplog.records.copy()
    with caplog.at_level("ERROR", "gunicorn.error"):
        await repo.get_project_page("numpy")

    assert len(caplog.records) == len(old_caplog_records) + 1
    assert any(
        record.message == "Yank configuration file must contain a dictionary."
        for record in caplog.records if record not in old_caplog_records
    )


@pytest.mark.asyncio
async def test_get_project_page_malformed(
    tmp_path: pathlib.PosixPath,
    source: MockRepository,
    caplog: pytest.LogCaptureFixture,
) -> None:
    file = tmp_path / "yank_config.json"
    file.write_text(
        data='{"numpy": "forgot reason!"}',
    )
    repo = ConfigurableYankRepository(
        source, file,
    )
    old_caplog_records = caplog.records.copy()
    with caplog.at_level("ERROR", "gunicorn.error"):
        await repo.get_project_page("numpy")

    assert len(caplog.records) == len(old_caplog_records) + 1
    assert any(
        record.message == "Invalid json structure for the project numpy"
        for record in caplog.records if record not in old_caplog_records
    )
