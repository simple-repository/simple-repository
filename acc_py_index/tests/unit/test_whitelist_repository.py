import pathlib

import pytest

from acc_py_index import errors
from acc_py_index.simple import model
from acc_py_index.simple.white_list_repository import WhitelistRepository

from ..fake_repository import FakeRepository


@pytest.mark.asyncio
async def test_special_get_project_page(tmp_path: pathlib.PosixPath) -> None:
    special_case_file = tmp_path / "special_cases.json"
    special_case_file.write_text('{"numpy": "url", "pandas": "url"}')

    repo = WhitelistRepository(
        source=FakeRepository(
            project_pages=[
                model.ProjectDetail(model.Meta("1.0"), "numpy", files=[]),
                model.ProjectDetail(model.Meta("1.0"), "tensorflow", files=[]),
            ],
        ),
        special_case_file=special_case_file,
    )

    resp = await repo.get_project_page("numpy")
    assert resp == model.ProjectDetail(model.Meta("1.0"), "numpy", files=[])

    with pytest.raises(errors.PackageNotFoundError, match="package"):
        await repo.get_project_page("package")

    with pytest.raises(errors.PackageNotFoundError, match="tensorflow"):
        await repo.get_project_page("tensorflow")


@pytest.mark.asyncio
async def test_get_project_list(tmp_path: pathlib.PosixPath) -> None:
    special_case_file = tmp_path / "special_cases.json"
    special_case_file.write_text('{"numpy": "url", "pandas": "url"}')

    repo = WhitelistRepository(
        source=FakeRepository(),
        special_case_file=special_case_file,
    )

    res = await repo.get_project_list()

    assert res == model.ProjectList(
        meta=model.Meta("1.0"),
        projects={model.ProjectListElement("numpy"), model.ProjectListElement("pandas")},
    )


@pytest.mark.asyncio
async def test_not_normalized_package(tmp_path: pathlib.PosixPath) -> None:
    special_case_file = tmp_path / "special_cases.json"
    special_case_file.write_text('{"numpy": "url", "pandas": "url"}')

    repo = WhitelistRepository(
        source=FakeRepository(),
        special_case_file=special_case_file,
    )
    with pytest.raises(errors.NotNormalizedProjectName):
        await repo.get_project_page("non_normalized")


@pytest.mark.asyncio
async def test_get_resources(tmp_path: pathlib.PosixPath) -> None:
    special_case_file = tmp_path / "special_cases.json"
    special_case_file.write_text('{"numpy": "url", "pandas": "url"}')

    repo = WhitelistRepository(
        source=FakeRepository(
            resources={
                "gunicorn-0.7.whl": model.Resource(
                    "gunicorn_url", model.ResourceType.REMOTE_RESOURCE,
                ),
                "numpy-0.7.whl": model.Resource(
                    "numpy_url", model.ResourceType.REMOTE_RESOURCE,
                ),
            },
        ),
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
    assert result.value == "numpy_url"


@pytest.mark.parametrize(
    "json_string", [
        "42", "true", '["a", "b"]', "null", '"ciao"',
    ],
)
@pytest.mark.asyncio
async def test_load_config_wrong_type(
    json_string: str,
    tmp_path: pathlib.PosixPath,
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
        WhitelistRepository(
            source=FakeRepository(),
            special_case_file=file,
        )


def test_load_config_wrong_format(
    tmp_path: pathlib.PosixPath,
) -> None:
    file = tmp_path / "yank_config.json"
    file.write_text(
        data='{"a": ["b", "c"]}',
    )
    with pytest.raises(
        errors.InvalidConfigurationError,
        match=(
            f'Invalid spcial case configuration file. {str(file)} '
            'must contain a dictionary mapping a project name to a tuple'
            ' containing a glob pattern and a yank reason.'
        ),
    ):
        WhitelistRepository(
            source=FakeRepository(),
            special_case_file=file,
        )


@pytest.mark.asyncio
async def test_load_config_malformed_json(
    tmp_path: pathlib.PosixPath,
) -> None:
    file = tmp_path / "yank_config.json"
    file.write_text(
        data='a',
    )
    with pytest.raises(
        errors.InvalidConfigurationError,
        match="Invalid json file",
    ):
        WhitelistRepository(
            source=FakeRepository(),
            special_case_file=file,
        )
