import pathlib
import typing
from unittest import mock
import zipfile

import aiosqlite
import pytest
import pytest_asyncio

from acc_py_index import errors
import acc_py_index.simple.model as model
from acc_py_index.simple.repositories.core import SimpleRepository
import acc_py_index.simple.repositories.metadata_injector as metadata_repository
from acc_py_index.tests.aiohttp_mock import MockClientSession

from .fake_repository import FakeRepository


def test_add_metadata_attribute() -> None:
    project_page = model.ProjectDetail(
       model.Meta("1.0"),
       "numpy",
       (
            model.File("numpy-1.0-any.whl", "/numpy-1.0-any.whl", {}, dist_info_metadata=None),
            model.File("numpy-1.0-any.whl", "/numpy-1.0-any.whl", {}, dist_info_metadata=False),
            model.File("numpy-1.0-any.tar.gz", "/numpy-1.0-any.tar.gz", {}),
            model.File(
                "numpy-1.1-any.whl", "/numpy-1.0-any.whl", {}, dist_info_metadata={"sha": "..."},
            ),
       ),
    )
    result = metadata_repository.add_metadata_attribute(project_page)

    assert result.files[0].dist_info_metadata is True
    assert result.files[1].dist_info_metadata is True
    assert result.files[2].dist_info_metadata is None
    assert result.files[3].dist_info_metadata == {"sha": "..."}


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


@pytest_asyncio.fixture
async def tmp_db(tmp_path: pathlib.Path) -> aiosqlite.Connection:
    async with aiosqlite.connect(tmp_path / "test.db") as db:
        yield db


@pytest.fixture
def repository(
    tmp_db: aiosqlite.Connection,
) -> metadata_repository.MetadataInjectorRepository:
    return metadata_repository.MetadataInjectorRepository(
        source=FakeRepository(
            project_pages=[
                model.ProjectDetail(
                    model.Meta("1.0"), "numpy", files=(
                        model.File("numpy-1.0-any.whl", "url", {}),
                        model.File("numpy-1.0.tar.gz", "url", {}),
                    ),
                ),
            ],
            resources={
                "numpy-1.0-any.whl": model.HttpResource(
                    url="numpy_url",
                ),
                "numpy-1.0.tar.gz": model.HttpResource(
                    url="numpy_url",
                ),
                "numpy-2.0-any.whl": model.LocalResource(
                    path=pathlib.Path("file/path"),
                ),
            },
        ),
        database=tmp_db,
        session=mock.AsyncMock(),
    )


@pytest.mark.asyncio
async def test_get_project_page(
    repository: metadata_repository.MetadataInjectorRepository,
) -> None:
    context = model.RequestContext(repository)
    result = await repository.get_project_page("numpy", context)
    assert result.files[0].dist_info_metadata is True


@pytest.mark.asyncio
async def test_get_resource__cached(
    repository: metadata_repository.MetadataInjectorRepository,
) -> None:
    context = model.RequestContext(repository)
    await repository._cache.set("name/resource.metadata", "cached_meta")

    response = await repository.get_resource("name", "resource.metadata", context)
    assert isinstance(response, model.TextResource)
    assert response.text == "cached_meta"


@pytest.mark.asyncio
async def test_get_resource__not_cached(
    repository: metadata_repository.MetadataInjectorRepository,
) -> None:
    context = model.RequestContext(repository)
    with mock.patch(
        "acc_py_index.simple.repositories.metadata_injector.download_metadata",
        mock.AsyncMock(return_value="downloaded_meta"),
    ):
        response = await repository.get_resource("numpy", "numpy-1.0-any.whl.metadata", context)

    assert isinstance(response, model.TextResource)
    assert response.text == "downloaded_meta"


@pytest.mark.asyncio
async def test_get_resource__local_resource(
    repository: metadata_repository.MetadataInjectorRepository,
) -> None:
    context = model.RequestContext(repository)
    with mock.patch(
        "acc_py_index.simple.repositories.metadata_injector.get_metadata_from_package",
        return_value="downloaded_meta",
    ):
        response = await repository.get_resource("numpy", "numpy-2.0-any.whl.metadata", context)

    assert isinstance(response, model.TextResource)
    assert response.text == "downloaded_meta"


@pytest.mark.asyncio
async def test_get_resource__not_valid_resource(
    tmp_db: aiosqlite.Connection,
) -> None:
    source_repo = mock.Mock(spec=SimpleRepository)
    source_repo.get_resource.side_effect = [
        errors.ResourceUnavailable('name'),
        model.TextResource(text='/etc/passwd'),
    ]
    repo = metadata_repository.MetadataInjectorRepository(
        source=typing.cast(SimpleRepository, source_repo),
        database=tmp_db,
        session=mock.AsyncMock(),
    )
    context = model.RequestContext(source_repo)
    with pytest.raises(errors.ResourceUnavailable, match='Unable to fetch the resource needed to extract the metadata'):
        await repo.get_resource("numpy", "numpy-1.0-any.whl.metadata", context)


@pytest.mark.parametrize(
    "resource_name", ["numpy-1.0-any.whl", "numpy-1.0.tar.gz"],
)
@pytest.mark.asyncio
async def test_get_resource__not_metadata(
    repository: metadata_repository.MetadataInjectorRepository,
    resource_name: str,
) -> None:
    context = model.RequestContext(repository)
    response = await repository.get_resource("numpy", resource_name, context)
    assert isinstance(response, model.HttpResource)
    assert response.url == "numpy_url"


@pytest.mark.asyncio
async def test_download_metadata() -> None:
    with (
        mock.patch(
            "acc_py_index.simple.repositories.metadata_injector.get_metadata_from_package",
        ) as get_metadata_from_package_mock,
        mock.patch("acc_py_index.utils.download_file") as download_file_mock,
    ):
        await metadata_repository.download_metadata("name", "url", MockClientSession())

    get_metadata_from_package_mock.assert_called_once()
    download_file_mock.assert_awaited_once()
