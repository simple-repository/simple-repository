import pathlib
import sqlite3
import typing
from unittest import mock

import aiohttp
import pytest

from acc_py_index.cache import CachedHttpRepository


@pytest.fixture
def repository(
    tmp_path: pathlib.Path,
) -> typing.Generator[CachedHttpRepository, None, None]:
    db_connection = sqlite3.connect(tmp_path / "tmp.db")
    repo = CachedHttpRepository(
        url="https://example.com/simple/",
        session=mock.MagicMock(),
        database=db_connection,
    )
    yield repo
    db_connection.close()


@pytest.mark.asyncio
async def test_fetch_simple_page_cache_miss(
    repository: CachedHttpRepository,
) -> None:
    response_mock = mock.AsyncMock(
        status=200,
        headers={
            "Content-Type": "application/json",
            "ETag": "etag",
        },
        text=mock.AsyncMock(return_value="body"),
    )

    repository.session.get.return_value.__aenter__.return_value = response_mock
    body, content_type = await repository._fetch_simple_page("url")
    assert body == "body"
    assert content_type == "application/json"
    response_mock.raise_for_status.assert_called_once()

    cached = repository._cache["url"]
    assert cached == "etag,application/json,body"


@pytest.mark.asyncio
async def test_fetch_simple_page_cache_hit_not_modified(
    repository: CachedHttpRepository,
) -> None:
    repository._cache["url"] = "stored-etag,stored-type,stored-body"
    response_mock = mock.AsyncMock(
        status=304,
    )
    repository.session.get.return_value.__aenter__.return_value = response_mock
    body, content_type = await repository._fetch_simple_page("url")
    assert body == "stored-body"
    assert content_type == "stored-type"


@pytest.mark.asyncio
async def test_fetch_simple_page_cache_hit_modified(
    repository: CachedHttpRepository,
) -> None:
    repository._cache["url"] = "stored-etag,stored-type,stored-body"
    response_mock = mock.AsyncMock(
        status=200,
        headers={
            "Content-Type": "new-type",
            "ETag": "new-etag",
        },
        text=mock.AsyncMock(return_value="new-body"),
    )
    repository.session.get.return_value.__aenter__.return_value = response_mock
    body, content_type = await repository._fetch_simple_page("url")
    assert body == "new-body"
    assert content_type == "new-type"
    assert repository._cache["url"] == "new-etag,new-type,new-body"


@pytest.mark.asyncio
async def test_fetch_simple_page_cache_hit_source_unreachable(
    repository: CachedHttpRepository,
) -> None:
    repository._cache["url"] = "stored-etag,stored-type,stored-body"
    repository.session.get.return_value.__aenter__.side_effect = aiohttp.ClientConnectionError()
    body, content_type = await repository._fetch_simple_page("url")
    assert body == "stored-body"
    assert content_type == "stored-type"
    assert repository._cache["url"] == "stored-etag,stored-type,stored-body"


@pytest.mark.asyncio
async def test_fetch_simple_page_cache_miss_source_unreachable(
    repository: CachedHttpRepository,
) -> None:
    repository.session.get.return_value.__aenter__.side_effect = aiohttp.ClientConnectionError()
    with pytest.raises(aiohttp.ClientConnectionError):
        body, content_type = await repository._fetch_simple_page("url")
