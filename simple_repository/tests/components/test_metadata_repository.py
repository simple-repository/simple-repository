# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import pathlib
import typing
from unittest import mock
import zipfile

import httpx
import pytest

from ... import errors, model
from ...components import core
from ...components.metadata_injector import MetadataInjectorRepository
from .fake_repository import FakeRepository
from .mock_compat import AsyncMock


@pytest.fixture
def repository() -> MetadataInjectorRepository:
    return MetadataInjectorRepository(
        source=FakeRepository(
            project_pages=[
                model.ProjectDetail(
                    model.Meta("1.0"),
                    "numpy",
                    files=(
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
        http_client=AsyncMock(),
    )


def test_add_metadata_attribute(repository: MetadataInjectorRepository) -> None:
    project_page = model.ProjectDetail(
        model.Meta("1.0"),
        "numpy",
        (
            model.File(
                "numpy-1.0-any.whl",
                "/numpy-1.0-any.whl",
                {},
                dist_info_metadata=None,
            ),
            model.File(
                "numpy-1.0-any.whl",
                "/numpy-1.0-any.whl",
                {},
                dist_info_metadata=False,
            ),
            model.File("numpy-1.0-any.tar.gz", "/numpy-1.0-any.tar.gz", {}),
            model.File(
                "numpy-1.1-any.whl",
                "/numpy-1.0-any.whl",
                {},
                dist_info_metadata={"sha": "..."},
            ),
        ),
    )
    result = repository._add_metadata_attribute(project_page)

    assert result.files[0].dist_info_metadata is True
    assert result.files[1].dist_info_metadata is True
    assert result.files[2].dist_info_metadata is None
    assert result.files[3].dist_info_metadata == {"sha": "..."}


@pytest.mark.parametrize(
    "namelist, metadata_name",
    [
        (
            [
                "my_package/files",
                "not_my_package-0.0.1.dist-info/METADATA",
                "my_package-0.0.1.dist-info/METADATA",
            ],
            "my_package-0.0.1.dist-info/METADATA",
        ),
        (
            [
                "my_package/files",
                "my_package-0.0.1.dist-info/METADATA",
                "My_Package-0.0.1.dist-info/METADATA",
            ],
            "my_package-0.0.1.dist-info/METADATA",
        ),
        (
            [
                "my_package/files",
                "My_Package-0.0.1.dist-info/METADATA",
            ],
            "My_Package-0.0.1.dist-info/METADATA",
        ),
        (
            [
                "my_package/files",
                "my.package-0.0.1.dist-info/METADATA",
            ],
            "my.package-0.0.1.dist-info/METADATA",
        ),
        (
            [
                "my_package/files",
                "my-package-0.0.1.dist-info/METADATA",
            ],
            "my-package-0.0.1.dist-info/METADATA",
        ),
    ],
)
def test_get_metadata_from_package(
    repository: MetadataInjectorRepository,
    namelist: typing.List[str],
    metadata_name: str,
) -> None:
    ziparchive = mock.MagicMock(spec=zipfile.ZipFile)
    ziparchive_ctx = ziparchive.__enter__.return_value
    read_method = ziparchive_ctx.read
    ziparchive_ctx.namelist.return_value = namelist

    with mock.patch("zipfile.ZipFile", return_value=ziparchive):
        repository._get_metadata_from_package(
            pathlib.Path("my_package") / "my_package-0.0.1-anylinux.whl",
        )

        read_method.assert_called_once_with(metadata_name)


def test_get_metadata_from_package__not_wheel(
    repository: MetadataInjectorRepository,
) -> None:
    with pytest.raises(ValueError, match="Package provided is not a wheel"):
        repository._get_metadata_from_package(
            pathlib.Path("my_package") / "package.tar.gz",
        )


@pytest.mark.parametrize(
    "namelist",
    [
        [
            "my_package/files",
            "not_my_package-0.0.1.dist-info/METADATA",
        ],
        [
            "my_package/files",
            "my_package.dist-info/METADATA",
        ],
        [
            "my_package/files",
            "my_package-0.0.1.dist-info/NOT_METADATA",
        ],
    ],
)
def test_get_metadata_from_package__missing_metadata(
    repository: MetadataInjectorRepository,
    namelist: typing.List[str],
) -> None:
    m_zipfile_cls = mock.MagicMock(spec=zipfile.ZipFile)
    m_zipfile_cls.return_value.__enter__.return_value.namelist.return_value = [
        "not_my_package-0.0.1.dist-info/METADATA",
    ]

    with mock.patch("zipfile.ZipFile", spec=zipfile.ZipFile, new=m_zipfile_cls):
        with pytest.raises(
            errors.InvalidPackageError,
            match="Provided wheel doesn't contain a metadata file.",
        ):
            repository._get_metadata_from_package(
                package_path=pathlib.Path("my_package")
                / "my_package-0.0.1-anylinux.whl",
            )


@pytest.mark.asyncio
async def test_get_project_page(
    repository: MetadataInjectorRepository,
) -> None:
    result = await repository.get_project_page("numpy")
    assert result.files[0].dist_info_metadata is True


@pytest.mark.asyncio
async def test_get_resource(
    repository: MetadataInjectorRepository,
) -> None:
    with mock.patch.object(
        repository,
        "_download_metadata",
        AsyncMock(return_value="downloaded_meta"),
    ):
        response = await repository.get_resource("numpy", "numpy-1.0-any.whl.metadata")

    assert isinstance(response, model.TextResource)
    assert response.text == "downloaded_meta"


@pytest.mark.asyncio
async def test_get_resource__local_resource(
    repository: MetadataInjectorRepository,
) -> None:
    with mock.patch.object(
        repository,
        "_get_metadata_from_package",
        return_value="downloaded_meta",
    ):
        response = await repository.get_resource("numpy", "numpy-2.0-any.whl.metadata")

    assert isinstance(response, model.TextResource)
    assert response.text == "downloaded_meta"


@pytest.mark.asyncio
async def test_get_resource__not_valid_resource() -> None:
    source_repo = mock.Mock(spec=core.SimpleRepository)
    source_repo.get_resource = AsyncMock(
        side_effect=[
            errors.ResourceUnavailable("name"),
            model.TextResource(text="/etc/passwd"),
        ],
    )
    repo = MetadataInjectorRepository(
        source=typing.cast(core.SimpleRepository, source_repo),
        http_client=AsyncMock(),
    )
    with pytest.raises(
        errors.ResourceUnavailable,
        match="Unable to fetch the resource needed to extract the metadata",
    ):
        await repo.get_resource("numpy", "numpy-1.0-any.whl.metadata")


@pytest.mark.parametrize(
    "resource_name",
    ["numpy-1.0-any.whl", "numpy-1.0.tar.gz"],
)
@pytest.mark.asyncio
async def test_get_resource__not_metadata(
    repository: MetadataInjectorRepository,
    resource_name: str,
) -> None:
    response = await repository.get_resource("numpy", resource_name)
    assert isinstance(response, model.HttpResource)
    assert response.url == "numpy_url"


@pytest.mark.asyncio
async def test_download_metadata(
    repository: MetadataInjectorRepository,
) -> None:
    with mock.patch.object(
        repository,
        "_get_metadata_from_package",
    ) as get_metadata_from_package_mock:
        with mock.patch(
            "simple_repository.utils.download_file",
            new_callable=AsyncMock,
        ) as download_file_mock:
            await repository._download_metadata("name", "url", httpx.AsyncClient())

    get_metadata_from_package_mock.assert_called_once()
    download_file_mock.assert_awaited_once()
