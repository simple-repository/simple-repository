# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import pathlib
import typing

import aiosqlite
import httpx
import pytest
import pytest_asyncio
from pytest_httpx import HTTPXMock

from ... import model
from ...components.http_cached import CachedHttpRepository


@pytest_asyncio.fixture
async def repository(
    tmp_path: pathlib.Path,
) -> typing.AsyncGenerator[CachedHttpRepository, None]:
    async with (
        aiosqlite.connect(tmp_path / "tmp.db") as db,
        httpx.AsyncClient() as client,
    ):
        yield CachedHttpRepository(
            url="https://example.com/simple/",
            http_client=client,
            database=db,
        )


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_miss(
    repository: CachedHttpRepository,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        content="new-body",
        headers={
            "Content-Type": "new-type",
            "ETag": "new-etag",
        },
    )

    body, content_type = await repository._fetch_simple_page("http://url")
    assert body == "new-body"
    assert content_type == "new-type"

    cached = await repository._cache.get("http://url")
    assert cached == "new-etag,new-type,new-body"


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_hit_not_modified(
    repository: CachedHttpRepository,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(status_code=304)

    await repository._cache.set("http://url", "stored-etag,stored-type,stored-body")
    body, content_type = await repository._fetch_simple_page("http://url")
    assert body == "stored-body"
    assert content_type == "stored-type"


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_hit_modified(
    repository: CachedHttpRepository,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        content="new-body",
        headers={
            "Content-Type": "new-type",
            "ETag": "new-etag",
        },
    )
    await repository._cache.set("http://url", "stored-etag,stored-type,stored-body")
    body, content_type = await repository._fetch_simple_page("http://url")
    assert body == "new-body"
    assert content_type == "new-type"
    assert await repository._cache.get("http://url") == "new-etag,new-type,new-body"


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_hit_source_unreachable(
    repository: CachedHttpRepository,
    httpx_mock: HTTPXMock,
) -> None:
    await repository._cache.set("url", "stored-etag,stored-type,stored-body")
    httpx_mock.add_exception(httpx.RequestError("error"))
    body, content_type = await repository._fetch_simple_page("url")
    assert body == "stored-body"
    assert content_type == "stored-type"
    assert await repository._cache.get("url") == "stored-etag,stored-type,stored-body"


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_miss_source_unreachable(
    repository: CachedHttpRepository,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_exception(httpx.RequestError("error"))
    with pytest.raises(httpx.RequestError, match="error"):
        await repository._fetch_simple_page("url")


@pytest.mark.asyncio
async def test_get_project_page__cached(
    repository: CachedHttpRepository,
    httpx_mock: HTTPXMock,
) -> None:
    await repository._cache.set(
        "https://example.com/simple/project/", "stored-etag,text/html," + """
        <a href="test1.whl#hash=test_hash">test1.whl</a>
        <a href="http://test2.whl">test2.whl</a>
    """,
    )
    httpx_mock.add_response(status_code=304)
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
    httpx_mock: HTTPXMock,
) -> None:
    await repository._cache.set(
        "https://example.com/simple/", "stored-etag,text/html," + """
        <a href="/p1/">p1</a>
        <a href="/p2/">p2</a>
    """,
    )
    httpx_mock.add_response(status_code=304)

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
