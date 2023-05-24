import pathlib
import sqlite3
from unittest import mock

from aiohttp import ClientSession
import pytest

from acc_py_index.simple import metadata_repository, model

from ..mock_repository import MockRepository


def test_add_metadata_attribute() -> None:
    project_page = model.ProjectDetail(
       model.Meta("1.0"),
       "numpy",
       [
            model.File("numpy-1.0-any.whl", "/numpy-1.0-any.whl", {}),
            model.File("numpy-1.0-any.tar.gz", "/numpy-1.0-any.tar.gz", {}),
            model.File(
                "numpy-1.1-any.whl", "/numpy-1.0-any.whl", {}, dist_info_metadata={"sha": "..."},
            ),
       ],
    )
    result = metadata_repository.add_metadata_attribute(project_page)

    assert result.files[0].dist_info_metadata is True
    assert result.files[1].dist_info_metadata is None
    assert result.files[2].dist_info_metadata == {"sha": "..."}


def test_get_metadata_from_package() -> None:
    m = mock.MagicMock()
    m.return_value = m
    m.__enter__.return_value = m

    with mock.patch('acc_py_index.simple.metadata_repository.zipfile.ZipFile', m):
        metadata_repository.get_metadata_from_package(pathlib.Path('trivial_dir'), 'trvial_name-0.0.1-anylinux.whl')
        m.read.assert_called_once_with('trvial_name-0.0.1.dist-info/METADATA')

    with pytest.raises(ValueError, match="Package provided is not a wheel"):
        metadata_repository.get_metadata_from_package(pathlib.Path('trivial_dir'), 'package.mp4')


@pytest.mark.asyncio
async def test_download_package(tmp_path: pathlib.PosixPath) -> None:
    download_url = "https://example.com/package.tar.gz"
    dest_file = tmp_path / "package.tar.gz"
    async with ClientSession() as session:
        await metadata_repository.download_package(download_url, dest_file, session)

    assert dest_file.exists()
    assert dest_file.stat().st_size > 0


@pytest.fixture
def repository(tmp_path: pathlib.Path) -> metadata_repository.MetadataRepository:
    db = sqlite3.connect(tmp_path / "test.db")
    return metadata_repository.MetadataRepository(
        source=MockRepository(
            project_pages=[
                model.ProjectDetail(
                    model.Meta("1.0"), "numpy", files=[model.File("numpy-1.0-any.whl", "url", {})],
                ),
            ],
            resources={"numpy-1.0-any.whl": "numpy_url"},
        ),
        database=db,
        session=mock.AsyncMock(),
    )


@pytest.mark.asyncio
async def test_get_project_page(repository: metadata_repository.MetadataRepository) -> None:
    result = await repository.get_project_page("numpy")
    assert result.files[0].dist_info_metadata is True


@pytest.mark.asyncio
async def test_get_resource_cached(repository: metadata_repository.MetadataRepository) -> None:
    repository._cache["name/resource.metadata"] = "cached_meta"

    response = await repository.get_resource("name", "resource.metadata")
    assert response.value == "cached_meta"
    assert response.type == model.ResourceType.metadata


@pytest.mark.asyncio
async def test_get_resource_not_cached(repository: metadata_repository.MetadataRepository) -> None:
    with mock.patch(
        "acc_py_index.simple.metadata_repository.download_metadata",
        mock.AsyncMock(return_value="downloaded_meta"),
    ):
        response = await repository.get_resource("numpy", "numpy-1.0-any.whl.metadata")

    assert response.value == "downloaded_meta"
    assert response.type == model.ResourceType.metadata


@pytest.mark.asyncio
async def test_get_resource_not_metadata(repository: metadata_repository.MetadataRepository) -> None:
    response = await repository.get_resource("numpy", "numpy-1.0-any.whl")
    assert response.value == "numpy_url"
    assert response.type == model.ResourceType.remote_resource
