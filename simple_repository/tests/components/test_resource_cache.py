# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from datetime import datetime
import os
import pathlib
from unittest import mock

import pytest

from ... import model
from ...components.resource_cache import ResourceCacheRepository
from .fake_repository import FakeRepository


@pytest.fixture
def repository(tmp_path: pathlib.Path) -> ResourceCacheRepository:
    http_resource = model.HttpResource("numpy_url/numpy-1.0-any.whl")
    http_resource.context["etag"] = "etag"
    source = FakeRepository(
        resources={
            "numpy-1.0-any.whl": http_resource,
            "numpy-1.0.tar.gz": model.LocalResource(pathlib.Path("numpy_path")),
            "numpy-1.1-any.whl": model.HttpResource("numpy_url/numpy-1.0-any.whl"),
        },
    )
    return ResourceCacheRepository(
        source=source,
        cache_path=tmp_path,
        session=mock.MagicMock(),
    )


@pytest.mark.asyncio
async def test_get_resource__cache_hit(repository: ResourceCacheRepository) -> None:
    (repository._cache_path / "numpy").mkdir()
    cached_file = repository._cache_path / "numpy" / "numpy-1.0-any.whl"
    cached_file.write_text("cached content")
    cached_info_file = repository._cache_path / "numpy" / "numpy-1.0-any.whl.info"
    # The content of the the info file matches the upstream cache
    cached_info_file.write_text("etag")

    context = model.RequestContext(repository)
    resource = await repository.get_resource(
        project_name="numpy",
        resource_name="numpy-1.0-any.whl",
        request_context=context,
    )
    # The cache returns a LocalResource pointing to
    # the cached file with the same etag as upstream
    assert isinstance(resource, model.LocalResource)
    assert resource.path == cached_file
    assert resource.context["etag"] == "etag"
    assert cached_file.read_text() == "cached content"


@pytest.mark.asyncio
async def test_get_resource__cache_miss(repository: ResourceCacheRepository) -> None:
    assert not (repository._cache_path / "numpy" / "numpy-1.0-any.whl.info").is_file()
    assert not (repository._cache_path / "numpy" / "numpy-1.0-any.whl").is_file()
    context = model.RequestContext(repository)

    with mock.patch(
        "simple_repository.utils.download_file",
        mock.AsyncMock(
            side_effect=lambda **kwargs: kwargs["dest_file"].touch(),
        ),
    ):
        response = await repository.get_resource(
            project_name="numpy",
            resource_name="numpy-1.0-any.whl",
            request_context=context,
        )

    # after the cache miss, the upstream file is downloaded and the info file is created.
    # The cache returns a LocalResource pointing to the downloaded file.
    assert isinstance(response, model.LocalResource)
    assert response.path == repository._cache_path / "numpy" / "numpy-1.0-any.whl"
    assert (repository._cache_path / "numpy" / "numpy-1.0-any.whl.info").is_file()
    assert (repository._cache_path / "numpy" / "numpy-1.0-any.whl").is_file()
    assert response.context.get("etag") == "etag"


@pytest.mark.asyncio
async def test_get_resource__cache_miss_local_resource(
    repository: ResourceCacheRepository,
) -> None:
    context = model.RequestContext(repository)
    resource = await repository.get_resource(
        project_name="numpy",
        resource_name="numpy-1.0.tar.gz",
        request_context=context,
    )

    # the cache doesn't store LocalResources. No cache file or info file is created.
    assert isinstance(resource, model.LocalResource)
    assert resource.path == pathlib.Path("numpy_path")
    assert not (repository._cache_path / "numpy" / "numpy-1.0.tar.gz.info").is_file()
    assert not (repository._cache_path / "numpy" / "numpy-1.0.tar.gz").is_file()


@pytest.mark.asyncio
async def test_get_resource__path_traversal(
    repository: ResourceCacheRepository,
) -> None:
    context = model.RequestContext(repository)
    with pytest.raises(
        ValueError,
        match="is not contained in",
    ):
        await repository.get_resource(
            project_name="not-used",
            resource_name="../../../etc/passwords",
            request_context=context,
        )


def test_resource_cache_init(tmp_path: pathlib.Path) -> None:
    real_repo = tmp_path / "dir" / "cache_repo"
    real_repo.mkdir(parents=True)

    symlink = tmp_path / "link"
    symlink.symlink_to(real_repo)

    repo = ResourceCacheRepository(
        source=mock.AsyncMock(),
        cache_path=symlink,
        session=mock.MagicMock(),
    )
    assert str(symlink) != str(real_repo)
    assert str(repo._cache_path) == str(real_repo)


def test_update_last_access(repository: ResourceCacheRepository) -> None:
    cached_info = repository._cache_path / "my_resource.ext.info"
    cached_info.touch()

    with mock.patch(
        "datetime.datetime",
        mock.Mock(
            now=mock.Mock(return_value=datetime.fromisoformat("2006-07-09")),
            fromisoformat=datetime.fromisoformat,
            spec=datetime,
        ),
    ):
        repository._update_last_access(cached_info)

    assert os.path.getatime(cached_info) == datetime.fromisoformat("2006-07-09").timestamp()

    with mock.patch(
        "datetime.datetime",
        mock.Mock(
            now=mock.Mock(return_value=datetime.fromisoformat("2025-07-09")),
            fromisoformat=datetime.fromisoformat,
            spec=datetime,
        ),
    ):
        repository._update_last_access(cached_info)

    assert os.path.getatime(cached_info) == datetime.fromisoformat("2025-07-09").timestamp()


@pytest.mark.asyncio
async def test_update_last_access__cache_hit_called(
    repository: ResourceCacheRepository,
) -> None:
    (repository._cache_path / "numpy").mkdir()
    cached_file = (repository._cache_path / "numpy" / "numpy-1.0-any.whl")
    cached_file.touch()
    cached_info_file = repository._cache_path / "numpy" / "numpy-1.0-any.whl.info"
    cached_info_file.write_text("etag")

    update_last_access_mock = mock.Mock()

    context = model.RequestContext(repository)
    with mock.patch.object(
        target=ResourceCacheRepository,
        attribute="_update_last_access",
        new=update_last_access_mock,
    ):
        await repository.get_resource(
            project_name="numpy",
            resource_name="numpy-1.0-any.whl",
            request_context=context,
        )

    update_last_access_mock.assert_called_once()


@pytest.mark.asyncio
async def test_update_last_access_for__cache_miss_local_not_called(
    repository: ResourceCacheRepository,
) -> None:
    update_last_access_for_mock = mock.Mock()
    context = model.RequestContext(repository)
    with mock.patch.object(
        target=ResourceCacheRepository,
        attribute="_update_last_access",
        new=update_last_access_for_mock,
    ):
        await repository.get_resource(
            project_name="numpy",
            resource_name="numpy-1.0.tar.gz",
            request_context=context,
        )
    update_last_access_for_mock.assert_not_called()


@pytest.mark.asyncio
async def test_update_last_access_for__cache_miss_remote_called(
    repository: ResourceCacheRepository,
) -> None:
    context = model.RequestContext(repository)
    update_last_access_for_mock = mock.Mock()
    with mock.patch(
        "simple_repository.utils.download_file",
        mock.AsyncMock(
            side_effect=lambda **kwargs: kwargs["dest_file"].touch(),
        ),
    ), mock.patch.object(
        target=ResourceCacheRepository,
        attribute="_update_last_access",
        new=update_last_access_for_mock,
    ):
        await repository.get_resource(
            project_name="project",
            resource_name="numpy-1.0-any.whl",
            request_context=context,
        )
    update_last_access_for_mock.assert_called_once()


@pytest.mark.asyncio
async def test_get_resource__no_cache_created_when_no_upstream_etag_exists(
    repository: ResourceCacheRepository,
) -> None:
    context = model.RequestContext(repository)
    resource = await repository.get_resource(
        project_name="numpy",
        resource_name="numpy-1.1-any.whl",
        request_context=context,
    )

    # Upstream doesn't set an etag so the HttpResource is not cached,
    # otherwise a LocalResource would have been returned
    # No cache file or info file gets created and an http resource is returned.
    assert isinstance(resource, model.HttpResource)
    assert not (repository._cache_path / "numpy" / "numpy-1.1-any.whl").is_file()
    assert not (repository._cache_path / "numpy" / "numpy-1.1-any.whl.info").is_file()
