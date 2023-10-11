# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import pathlib
import typing
from unittest import mock

import aiohttp
import aiosqlite
import pytest
import pytest_asyncio

from ... import model
from ...components.http_cached import CachedHttpRepository


@pytest_asyncio.fixture
async def repository(
    tmp_path: pathlib.Path,
) -> typing.AsyncGenerator[CachedHttpRepository, None]:
    async with aiosqlite.connect(tmp_path / "tmp.db") as db:
        yield CachedHttpRepository(
            url="https://example.com/simple/",
            session=mock.Mock(),
            database=db,
        )


@pytest.fixture
def response_mock() -> mock.AsyncMock:
    return mock.AsyncMock(
        status=200,
        headers={
            "Content-Type": "new-type",
            "ETag": "new-etag",
        },
        text=mock.AsyncMock(return_value="new-body"),
    )


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_miss(
    repository: CachedHttpRepository,
    response_mock: mock.AsyncMock,
) -> None:
    request_context_mock = mock.AsyncMock()
    request_context_mock.__aenter__.return_value = response_mock
    repository.session.get.return_value = request_context_mock

    body, content_type = await repository._fetch_simple_page("url")
    assert body == "new-body"
    assert content_type == "new-type"

    cached = await repository._cache.get("url")
    assert cached == "new-etag,new-type,new-body"


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_hit_not_modified(
    repository: CachedHttpRepository,
    response_mock: mock.AsyncMock,
) -> None:
    await repository._cache.set("url", "stored-etag,stored-type,stored-body")
    response_mock.status = 304
    request_context_mock = mock.AsyncMock()
    request_context_mock.__aenter__.return_value = response_mock
    repository.session.get.return_value = request_context_mock
    body, content_type = await repository._fetch_simple_page("url")
    assert body == "stored-body"
    assert content_type == "stored-type"


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_hit_modified(
    repository: CachedHttpRepository,
    response_mock: mock.AsyncMock,
) -> None:
    await repository._cache.set("url", "stored-etag,stored-type,stored-body")
    request_context_mock = mock.AsyncMock()
    request_context_mock.__aenter__.return_value = response_mock
    repository.session.get.return_value = request_context_mock
    body, content_type = await repository._fetch_simple_page("url")
    assert body == "new-body"
    assert content_type == "new-type"
    assert await repository._cache.get("url") == "new-etag,new-type,new-body"


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_hit_source_unreachable(
    repository: CachedHttpRepository,
) -> None:
    await repository._cache.set("url", "stored-etag,stored-type,stored-body")
    request_context_mock = mock.AsyncMock()
    request_context_mock.__aenter__.side_effect = aiohttp.ClientConnectionError()
    repository.session.get.return_value = request_context_mock
    body, content_type = await repository._fetch_simple_page("url")
    assert body == "stored-body"
    assert content_type == "stored-type"
    assert await repository._cache.get("url") == "stored-etag,stored-type,stored-body"


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_miss_source_unreachable(
    repository: CachedHttpRepository,
) -> None:
    request_context_mock = mock.AsyncMock()
    request_context_mock.__aenter__.side_effect = aiohttp.ClientConnectionError()
    repository.session.get.return_value = request_context_mock
    with pytest.raises(aiohttp.ClientConnectionError):
        await repository._fetch_simple_page("url")


@pytest.mark.asyncio
async def test_get_project_page__cached(
    repository: CachedHttpRepository,
    response_mock: mock.AsyncMock,
) -> None:
    await repository._cache.set(
        "https://example.com/simple/project/", "stored-etag,text/html," + """
        <a href="test1.whl#hash=test_hash">test1.whl</a>
        <a href="http://test2.whl">test2.whl</a>
    """,
    )
    response_mock.status = 304
    request_context_mock = mock.AsyncMock()
    request_context_mock.__aenter__.side_effect = aiohttp.ClientConnectionError()
    repository.session.get.return_value = request_context_mock

    response = await repository.get_project_page("project")

    assert response == model.ProjectDetail(
        name="project",
        meta=model.Meta(
            api_version="1.0",
        ),
        files=(
            model.File(
                filename="test1.whl",
                url="https://example.com/simple/project/test1.whl",
                hashes={"hash": "test_hash"},
            ),
            model.File(
                filename="test2.whl",
                url="http://test2.whl",
                hashes={},
            ),
        ),
    )


@pytest.mark.asyncio
async def test_get_project_list__cached(
    repository: CachedHttpRepository,
    response_mock: mock.AsyncMock,
) -> None:
    await repository._cache.set(
        "https://example.com/simple/", "stored-etag,text/html," + """
        <a href="/p1/">p1</a>
        <a href="/p2/">p2</a>
    """,
    )
    response_mock.status = 304
    request_context_mock = mock.AsyncMock()
    request_context_mock.__aenter__.side_effect = aiohttp.ClientConnectionError()
    repository.session.get.return_value = request_context_mock

    resp = await repository.get_project_list()
    assert resp == model.ProjectList(
        meta=model.Meta(
            api_version="1.0",
        ),
        projects=frozenset([
            model.ProjectListElement(name="p1"),
            model.ProjectListElement(name="p2"),
        ]),
    )
