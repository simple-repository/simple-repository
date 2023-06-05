import pathlib
import sqlite3
import typing
from unittest import mock
import zipfile

import pytest

from acc_py_index import errors
from acc_py_index.simple import metadata_repository, model
from acc_py_index.simple.repositories import SimpleRepository

from ..fake_repository import FakeRepository


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
    m_zipfile_cls = mock.MagicMock(spec=zipfile.ZipFile)
    read_method = m_zipfile_cls.return_value.__enter__.return_value.read

    with mock.patch('zipfile.ZipFile', spec=zipfile.ZipFile, new=m_zipfile_cls):
        metadata_repository.get_metadata_from_package(pathlib.Path('trivial_dir') / 'trvial_name-0.0.1-anylinux.whl')
        read_method.assert_called_once_with('trvial_name-0.0.1.dist-info/METADATA')

    with pytest.raises(ValueError, match="Package provided is not a wheel"):
        metadata_repository.get_metadata_from_package(pathlib.Path('trivial_dir') / 'package.mp4')


def test_get_metadata_from_package__missing_metadata() -> None:
    m_zipfile_cls = mock.MagicMock(spec=zipfile.ZipFile)
    read_method = m_zipfile_cls.return_value.__enter__.return_value.read
    read_method.side_effect = KeyError()

    with mock.patch('zipfile.ZipFile', spec=zipfile.ZipFile, new=m_zipfile_cls):
        with pytest.raises(
            errors.InvalidPackageError,
            match="Provided wheel doesn't contain a metadata file.",
        ) as exc_info:
            metadata_repository.get_metadata_from_package(
                package_path=pathlib.Path('trivial_dir') / 'trvial_name-0.0.1-anylinux.whl',
            )
    assert isinstance(exc_info.value.__cause__, KeyError)


@pytest.fixture
def tmp_db(tmp_path: pathlib.Path) -> sqlite3.Connection:
    return sqlite3.connect(tmp_path / "test.db")


@pytest.fixture
def repository(tmp_db: sqlite3.Connection) -> metadata_repository.MetadataInjectorRepository:
    return metadata_repository.MetadataInjectorRepository(
        source=FakeRepository(
            project_pages=[
                model.ProjectDetail(
                    model.Meta("1.0"), "numpy", files=[
                        model.File("numpy-1.0-any.whl", "url", {}),
                        model.File("numpy-1.0.tar.gz", "url", {}),
                    ],
                ),
            ],
            resources={
                "numpy-1.0-any.whl": "numpy_url",
                "numpy-1.0.tar.gz": "numpy_url",
            },
        ),
        database=tmp_db,
        session=mock.AsyncMock(),
    )


@pytest.mark.asyncio
async def test_get_project_page(repository: metadata_repository.MetadataInjectorRepository) -> None:
    result = await repository.get_project_page("numpy")
    assert result.files[0].dist_info_metadata is True


@pytest.mark.asyncio
async def test_get_resource__cached(repository: metadata_repository.MetadataInjectorRepository) -> None:
    repository._cache["name/resource.metadata"] = "cached_meta"

    response = await repository.get_resource("name", "resource.metadata")
    assert response.value == "cached_meta"
    assert response.type == model.ResourceType.METADATA


@pytest.mark.asyncio
async def test_get_resource__not_cached(repository: metadata_repository.MetadataInjectorRepository) -> None:
    with mock.patch(
        "acc_py_index.simple.metadata_repository.download_metadata",
        mock.AsyncMock(return_value="downloaded_meta"),
    ):
        response = await repository.get_resource("numpy", "numpy-1.0-any.whl.metadata")

    assert response.value == "downloaded_meta"
    assert response.type == model.ResourceType.METADATA


@pytest.mark.asyncio
async def test_get_resource__not_http_resource(tmp_db: sqlite3.Connection) -> None:
    source_repo = mock.Mock(spec=SimpleRepository)
    source_repo.get_resource.side_effect = [errors.ResourceUnavailable('name'), model.Resource('/etc/passwd', model.ResourceType.METADATA)]
    repo = metadata_repository.MetadataInjectorRepository(
        source=typing.cast(SimpleRepository, source_repo),
        database=tmp_db,
        session=mock.AsyncMock(),
    )
    with pytest.raises(errors.ResourceUnavailable, match='Unable to fetch the resource needed to extract the metadata'):
        await repo.get_resource("numpy", "numpy-1.0-any.whl.metadata")


@pytest.mark.parametrize(
    "resource_name", ["numpy-1.0-any.whl", "numpy-1.0.tar.gz"],
)
@pytest.mark.asyncio
async def test_get_resource__not_metadata(
    repository: metadata_repository.MetadataInjectorRepository,
    resource_name: str,
) -> None:
    response = await repository.get_resource("numpy", resource_name)
    assert response.value == "numpy_url"
    assert response.type == model.ResourceType.REMOTE_RESOURCE


@pytest.mark.asyncio
async def test_download_metadata() -> None:
    mock_session = mock.Mock()
    get_metadata_from_package_mock = mock.Mock()
    download_file_mock = mock.AsyncMock()

    with mock.patch(
        "acc_py_index.simple.metadata_repository.get_metadata_from_package",
        get_metadata_from_package_mock,
    ), mock.patch(
        "acc_py_index.utils.download_file",
        download_file_mock,
    ):
        await metadata_repository.download_metadata("name", "url", mock_session)

    get_metadata_from_package_mock.assert_called_once()
    download_file_mock.assert_awaited_once()
