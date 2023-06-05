import pathlib

import pytest

from acc_py_index import errors
from acc_py_index.simple import model
from acc_py_index.simple.yank_repository import ConfigurableYankRepository
from acc_py_index.tests.fake_repository import FakeRepository


@pytest.fixture
def source() -> FakeRepository:
    return FakeRepository(
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
    source: FakeRepository,
) -> None:
    file = tmp_path / "yank_config.json"
    file.write_text(
        data='{"numpy": ["*.whl", "bad"], "pandas": ["*[!.whl]", "not supported"]}',
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
def test_load_config_wrong_type(
    json_string: str,
    tmp_path: pathlib.PosixPath,
    source: FakeRepository,
) -> None:
    file = tmp_path / "yank_config.json"
    file.write_text(
        data=json_string,
    )
    with pytest.raises(
        errors.InvalidConfigurationError,
        match=(
            f"Invalid configuration file. {str(file)} must contain a dictionary."
        ),
    ):
        ConfigurableYankRepository(
            source=source,
            yank_config_file=file,
        )


def test_load_config_wrong_format(
    tmp_path: pathlib.PosixPath,
    source: FakeRepository,
) -> None:
    file = tmp_path / "yank_config.json"
    file.write_text(
        data='{"a": "b"}',
    )
    with pytest.raises(
        errors.InvalidConfigurationError,
        match=(
            f'Invalid yank configuration file. {str(file)} must'
            ' contain a dictionary mapping a project name to a tuple'
            ' containing a glob pattern and a yank reason.'
        ),
    ):
        ConfigurableYankRepository(
            source=source,
            yank_config_file=file,
        )


def test_load_config_malformed_json(
    tmp_path: pathlib.PosixPath,
    source: FakeRepository,
) -> None:
    file = tmp_path / "yank_config.json"
    file.write_text(
        data='a',
    )
    with pytest.raises(
        errors.InvalidConfigurationError,
        match="Invalid json file",
    ):
        ConfigurableYankRepository(
            source=source,
            yank_config_file=file,
        )
