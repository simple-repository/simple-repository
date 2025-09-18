# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

from datetime import datetime
import logging
import os
import pathlib
from unittest import mock

import pytest

from ... import errors, model
from ...components import core
from ...components.resource_cache import ResourceCacheRepository
from .fake_repository import FakeRepository
from .mock_compat import AsyncMock


@pytest.fixture
def repository(tmp_path: pathlib.Path) -> ResourceCacheRepository:
    http_resource = model.HttpResource("url/http-1.0-any.whl")
    http_resource.context["etag"] = "etag"

    not_to_cache_resource = model.HttpResource(
        "url/uncacheable-1.0-any.whl",
        to_cache=False,
    )
    not_to_cache_resource.context["etag"] = "etag"
    source = FakeRepository(
        project_pages=[
            model.ProjectDetail(model.Meta("1.0"), "http", files=()),
            model.ProjectDetail(model.Meta("1.0"), "local", files=()),
            model.ProjectDetail(model.Meta("1.0"), "http-no-etag", files=()),
            model.ProjectDetail(model.Meta("1.0"), "uncacheable", files=()),
            model.ProjectDetail(model.Meta("1.0"), "resource", files=()),
        ],
        resources={
            "http-1.0-any.whl": http_resource,
            "local-1.0.tar.gz": model.LocalResource(pathlib.Path("path")),
            "http_no_etag-1.0-any.whl": model.HttpResource(
                "url/http_no_etag-1.0-any.whl",
            ),
            "uncacheable-1.0-any.whl": not_to_cache_resource,
        },
    )
    return ResourceCacheRepository(
        source=source,
        cache_path=tmp_path,
        http_client=mock.MagicMock(),
    )


@pytest.mark.asyncio
async def test_get_resource__cache_hit(repository: ResourceCacheRepository) -> None:
    (repository._cache_path / "http").mkdir()
    cached_file = repository._cache_path / "http" / "http-1.0-any.whl"
    cached_file.write_text("cached content")
    cached_info_file = repository._cache_path / "http" / "http-1.0-any.whl.info"
    # The content of the the info file matches the upstream cache
    cached_info_file.write_text("etag")

    resource = await repository.get_resource(
        project_name="http",
        resource_name="http-1.0-any.whl",
    )
    # The cache returns a LocalResource pointing to
    # the cached file with the same etag as upstream
    assert isinstance(resource, model.LocalResource)
    assert resource.path == cached_file
    assert resource.context["etag"] == "etag"
    assert cached_file.read_text() == "cached content"


@pytest.mark.asyncio
async def test_get_resource__cache_miss__wrong_etag(
    repository: ResourceCacheRepository,
) -> None:
    (repository._cache_path / "http").mkdir()
    cached_file = repository._cache_path / "http" / "http-1.0-any.whl"
    cached_file.write_text("invalid cached content")
    cached_info_file = repository._cache_path / "http" / "http-1.0-any.whl.info"
    # The content of the the info file matches the upstream cache
    cached_info_file.write_text("wrong_etag")

    with mock.patch(
        "simple_repository.utils.download_file",
        AsyncMock(
            side_effect=lambda **kwargs: kwargs["dest_file"].touch(),
        ),
    ):
        response = await repository.get_resource(
            project_name="http",
            resource_name="http-1.0-any.whl",
        )

    # after the cache miss, the upstream file is downloaded and the info file is created.
    # The cache returns a LocalResource pointing to the downloaded file.
    assert isinstance(response, model.LocalResource)
    assert response.path == repository._cache_path / "http" / "http-1.0-any.whl"
    assert (
        repository._cache_path / "http" / "http-1.0-any.whl.info"
    ).read_text() == "etag"
    assert (
        repository._cache_path / "http" / "http-1.0-any.whl"
    ).read_text() != "invalid cached content"


@pytest.mark.asyncio
async def test_get_resource__cache_miss__no_etag(
    repository: ResourceCacheRepository,
) -> None:
    assert not (repository._cache_path / "http" / "http-1.0-any.whl.info").is_file()
    assert not (repository._cache_path / "http" / "http-1.0-any.whl").is_file()

    with mock.patch(
        "simple_repository.utils.download_file",
        AsyncMock(
            side_effect=lambda **kwargs: kwargs["dest_file"].touch(),
        ),
    ):
        response = await repository.get_resource(
            project_name="http",
            resource_name="http-1.0-any.whl",
        )

    # after the cache miss, the upstream file is downloaded and the info file is created.
    # The cache returns a LocalResource pointing to the downloaded file.
    assert isinstance(response, model.LocalResource)
    assert response.path == repository._cache_path / "http" / "http-1.0-any.whl"
    assert (repository._cache_path / "http" / "http-1.0-any.whl.info").is_file()
    assert (repository._cache_path / "http" / "http-1.0-any.whl").is_file()
    assert response.context.get("etag") == "etag"


@pytest.mark.asyncio
async def test_get_resource__cache_miss_local_resource(
    repository: ResourceCacheRepository,
) -> None:
    resource = await repository.get_resource(
        project_name="local",
        resource_name="local-1.0.tar.gz",
    )

    # the cache doesn't store LocalResources. No cache file or info file is created.
    assert isinstance(resource, model.LocalResource)
    assert resource.path == pathlib.Path("path")
    assert not (repository._cache_path / "local" / "local-1.0.tar.gz.info").is_file()
    assert not (repository._cache_path / "local" / "local-1.0.tar.gz").is_file()


@pytest.mark.asyncio
async def test_get_resource__path_traversal(
    repository: ResourceCacheRepository,
) -> None:
    with pytest.raises(
        ValueError,
        match="is not contained in",
    ):
        await repository.get_resource(
            project_name="not-used",
            resource_name="../../../etc/passwords",
        )


@pytest.mark.asyncio
async def test_get_resource__source_unavailable_cache_hit(
    tmp_path: pathlib.Path,
) -> None:
    source = AsyncMock(
        spec=core.SimpleRepository,
        get_resource=AsyncMock(side_effect=errors.SourceRepositoryUnavailable),
    )

    (tmp_path / "project-name").mkdir()

    (tmp_path / "project-name" / "resource-name.info").write_text("etag")
    (tmp_path / "project-name" / "resource-name").write_text("content")

    repository = ResourceCacheRepository(
        source=source,
        cache_path=tmp_path,
        http_client=mock.MagicMock(),
    )

    resource = await repository.get_resource("project-name", "resource-name")
    assert isinstance(resource, model.LocalResource)
    assert resource.path == tmp_path / "project-name" / "resource-name"


@pytest.mark.asyncio
async def test_get_resource__source_unavailable_cache_hit__falback_disabled(
    tmp_path: pathlib.Path,
) -> None:
    source = AsyncMock(
        spec=core.SimpleRepository,
        get_resource=AsyncMock(side_effect=errors.SourceRepositoryUnavailable),
    )

    (tmp_path / "project-name").mkdir()

    (tmp_path / "project-name" / "resource-name.info").write_text("etag")
    (tmp_path / "project-name" / "resource-name").write_text("content")

    repository = ResourceCacheRepository(
        source=source,
        cache_path=tmp_path,
        http_client=mock.MagicMock(),
        fallback_to_cache=False,
    )

    with pytest.raises(errors.SourceRepositoryUnavailable):
        await repository.get_resource("project-name", "resource-name")


@pytest.mark.asyncio
async def test_get_resource__source_unavailable_cache_hit__log(
    tmp_path: pathlib.Path,
) -> None:
    source = AsyncMock(
        spec=core.SimpleRepository,
        get_resource=AsyncMock(side_effect=errors.SourceRepositoryUnavailable),
    )

    (tmp_path / "project-name").mkdir()

    (tmp_path / "project-name" / "resource-name.info").write_text("etag")
    (tmp_path / "project-name" / "resource-name").write_text("content")

    mock_logger = mock.Mock(spec=logging.Logger)

    repository = ResourceCacheRepository(
        source=source,
        cache_path=tmp_path,
        http_client=mock.MagicMock(),
        logger=mock_logger,
    )

    await repository.get_resource("project-name", "resource-name")
    mock_logger.error.assert_called_once_with(
        "Upstream unavailable, served cached project-name:resource-name",
    )


@pytest.mark.asyncio
async def test_get_resource__source_unavailable_cache_miss(
    tmp_path: pathlib.Path,
) -> None:
    source = AsyncMock(
        spec=core.SimpleRepository,
        get_resource=AsyncMock(side_effect=errors.SourceRepositoryUnavailable),
    )

    repository = ResourceCacheRepository(
        source=source,
        cache_path=tmp_path,
        http_client=mock.MagicMock(),
    )

    with pytest.raises(errors.SourceRepositoryUnavailable):
        await repository.get_resource("project-name", "resource-name")


@pytest.mark.asyncio
async def test_get_resource__no_cache_created_when_no_upstream_etag_exists(
    repository: ResourceCacheRepository,
) -> None:
    resource = await repository.get_resource(
        project_name="http-no-etag",
        resource_name="http_no_etag-1.0-any.whl",
    )

    # Upstream doesn't set an etag so the HttpResource is not cached,
    # otherwise a LocalResource would have been returned
    # No cache file or info file gets created and an http resource is returned.
    assert isinstance(resource, model.HttpResource)
    assert not (
        repository._cache_path / "http-no-etag" / "http_no_etag-1.0-any.whl"
    ).is_file()
    assert not (
        repository._cache_path / "http-no-etag" / "http_no_etag-1.0-any.whl.info"
    ).is_file()


@pytest.mark.parametrize(
    "resource",
    [
        model.HttpResource(url="url", to_cache=False),
        model.LocalResource(path=pathlib.Path("."), to_cache=False),
        model.TextResource(text="text", to_cache=False),
    ],
)
@pytest.mark.asyncio
async def test_get_resource__no_cache_created_when_to_cache_is_false(
    resource: model.Resource,
    tmp_path: pathlib.Path,
) -> None:
    resource.context["etag"] = "etag"

    repository = ResourceCacheRepository(
        source=FakeRepository(
            project_pages=[
                model.ProjectDetail(model.Meta("1.0"), "resource", files=()),
            ],
            resources={"resource-1.0-any.whl": resource},
        ),
        cache_path=tmp_path,
        http_client=mock.MagicMock(),
    )

    result = await repository.get_resource(
        project_name="resource",
        resource_name="resource-1.0-any.whl",
    )

    # Upstream sets an etag but the to_cache attribute is False so the resource is not cached.
    # No cache file or info file gets created and an same resource is returned.
    assert resource == result
    assert not (repository._cache_path / "resource" / "resource-1.0-any.whl").is_file()
    assert not (
        repository._cache_path / "resource" / "resource-1.0-any.whl.info"
    ).is_file()


@pytest.mark.asyncio
async def test_get_resource__source_raised_not_modified__request_etag_invalid(
    repository: ResourceCacheRepository,
) -> None:
    # Upstream raised not modified and the request context misses the etag.
    repository.source = mock.Mock(get_resource=AsyncMock(side_effect=model.NotModified))

    (repository._cache_path / "http").mkdir()
    cached_file = repository._cache_path / "http" / "http-1.0-any.whl"
    cached_file.write_text("cached content")
    cached_info_file = repository._cache_path / "http" / "http-1.0-any.whl.info"
    # The content of the the info file matches the upstream cache
    cached_info_file.write_text("etag")

    resource = await repository.get_resource(
        project_name="http",
        resource_name="http-1.0-any.whl",
    )
    # The cache returns a LocalResource pointing to
    # the cached file with the same etag as upstream
    assert isinstance(resource, model.LocalResource)
    assert resource.path == cached_file
    assert resource.context["etag"] == "etag"
    assert cached_file.read_text() == "cached content"


@pytest.mark.asyncio
async def test_get_resource__source_raised_not_modified__request_etag_valid(
    repository: ResourceCacheRepository,
) -> None:
    # Upstream raised not modified and the request etag matches.
    repository.source = mock.Mock(get_resource=AsyncMock(side_effect=model.NotModified))

    (repository._cache_path / "http").mkdir()
    cached_file = repository._cache_path / "http" / "http-1.0-any.whl"
    cached_file.write_text("cached content")
    cached_info_file = repository._cache_path / "http" / "http-1.0-any.whl.info"
    # The content of the the info file matches the upstream cache
    cached_info_file.write_text("etag")

    context = model.RequestContext({"etag": "etag"})

    with pytest.raises(model.NotModified):
        await repository.get_resource(
            project_name="http",
            resource_name="http-1.0-any.whl",
            request_context=context,
        )


def test_resource_cache_init(tmp_path: pathlib.Path) -> None:
    real_repo = tmp_path / "dir" / "cache_repo"
    real_repo.mkdir(parents=True)

    symlink = tmp_path / "link"
    symlink.symlink_to(real_repo)

    repo = ResourceCacheRepository(
        source=AsyncMock(),
        cache_path=symlink,
        http_client=mock.MagicMock(),
    )
    assert str(symlink) != str(real_repo)
    assert str(repo._cache_path) == str(real_repo)


def test_update_last_access(repository: ResourceCacheRepository) -> None:
    cached_info = repository._cache_path / "my_resource.ext.info"
    cached_info.touch()

    with mock.patch(
        "simple_repository.components.resource_cache.datetime",
        mock.Mock(
            now=mock.Mock(return_value=datetime.fromisoformat("2006-07-09")),
            fromisoformat=datetime.fromisoformat,
            spec=datetime,
        ),
    ):
        repository._update_last_access(cached_info)

    assert (
        os.path.getatime(cached_info)
        == datetime.fromisoformat("2006-07-09").timestamp()
    )

    with mock.patch(
        "simple_repository.components.resource_cache.datetime",
        mock.Mock(
            now=mock.Mock(return_value=datetime.fromisoformat("2025-07-09")),
            fromisoformat=datetime.fromisoformat,
            spec=datetime,
        ),
    ):
        repository._update_last_access(cached_info)

    assert (
        os.path.getatime(cached_info)
        == datetime.fromisoformat("2025-07-09").timestamp()
    )


@pytest.mark.asyncio
async def test_update_last_access__cache_hit_called(
    repository: ResourceCacheRepository,
) -> None:
    (repository._cache_path / "http").mkdir()
    cached_file = repository._cache_path / "http" / "http-1.0-any.whl"
    cached_file.touch()
    cached_info_file = repository._cache_path / "http" / "http-1.0-any.whl.info"
    cached_info_file.write_text("etag")

    update_last_access_mock = mock.Mock()

    with mock.patch.object(
        target=ResourceCacheRepository,
        attribute="_update_last_access",
        new=update_last_access_mock,
    ):
        await repository.get_resource(
            project_name="http",
            resource_name="http-1.0-any.whl",
        )

    update_last_access_mock.assert_called_once()


@pytest.mark.asyncio
async def test_update_last_access_for__cache_miss_local_not_called(
    repository: ResourceCacheRepository,
) -> None:
    update_last_access_for_mock = mock.Mock()
    with mock.patch.object(
        target=ResourceCacheRepository,
        attribute="_update_last_access",
        new=update_last_access_for_mock,
    ):
        await repository.get_resource(
            project_name="local",
            resource_name="local-1.0.tar.gz",
        )
    update_last_access_for_mock.assert_not_called()


@pytest.mark.asyncio
async def test_update_last_access_for__cache_miss_remote_called(
    repository: ResourceCacheRepository,
) -> None:
    update_last_access_for_mock = mock.Mock()
    with mock.patch(
        "simple_repository.utils.download_file",
        AsyncMock(
            side_effect=lambda **kwargs: kwargs["dest_file"].touch(),
        ),
    ), mock.patch.object(
        target=ResourceCacheRepository,
        attribute="_update_last_access",
        new=update_last_access_for_mock,
    ):
        await repository.get_resource(
            project_name="http",
            resource_name="http-1.0-any.whl",
        )
    update_last_access_for_mock.assert_called_once()


@pytest.mark.asyncio
async def test_store_resource__http_resource(
    repository: ResourceCacheRepository,
    tmp_path: pathlib.Path,
) -> None:
    http_resource = model.HttpResource(url="my_url")
    cache_path = tmp_path / "cache"

    with mock.patch(
        "simple_repository.utils.download_file",
        AsyncMock(
            side_effect=lambda **kwargs: kwargs["dest_file"].write_text("http content"),
        ),
    ):
        await repository._store_resource(
            resource=http_resource,
            upstream_etag="etag",
            resource_path=cache_path,
            resource_info_path=cache_path.with_suffix(".metadata"),
        )

    assert cache_path.read_text() == "http content"
    assert cache_path.with_suffix(".metadata").read_text() == "etag"


@pytest.mark.asyncio
async def test_store_resource__local_resource(
    repository: ResourceCacheRepository,
    tmp_path: pathlib.Path,
) -> None:
    file_path = tmp_path / "file"
    (tmp_path / "file").write_text("file_content")
    cache_path = tmp_path / "cache"
    local_resource = model.LocalResource(file_path)

    await repository._store_resource(
        resource=local_resource,
        upstream_etag="etag",
        resource_path=cache_path,
        resource_info_path=cache_path.with_suffix(".metadata"),
    )

    assert cache_path.read_text() == "file_content"
    assert cache_path.with_suffix(".metadata").read_text() == "etag"


@pytest.mark.asyncio
async def test_store_resource__text_resource(
    repository: ResourceCacheRepository,
    tmp_path: pathlib.Path,
) -> None:
    cache_path = tmp_path / "cache"
    text_resource = model.TextResource("my_text")

    await repository._store_resource(
        resource=text_resource,
        upstream_etag="etag",
        resource_path=cache_path,
        resource_info_path=cache_path.with_suffix(".metadata"),
    )

    assert cache_path.read_text() == "my_text"
    assert cache_path.with_suffix(".metadata").read_text() == "etag"
