# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

from datetime import datetime
import os
import pathlib
import typing
from unittest import mock

import httpx
import pytest
import pytest_asyncio

from ... import model
from ...components.http_cached import CachedHttpRepository

if typing.TYPE_CHECKING:
    import pytest_httpx


@pytest_asyncio.fixture
async def repository(
    tmp_path: pathlib.Path,
) -> typing.AsyncGenerator[CachedHttpRepository, None]:
    async with httpx.AsyncClient() as client:
        yield CachedHttpRepository(
            url="https://example.com/simple/",
            http_client=client,
            cache_path=tmp_path,
        )


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_miss(
    repository: CachedHttpRepository,
    httpx_mock: pytest_httpx.HTTPXMock,
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

    cached = repository._get_from_cache("http://url")
    assert cached == "new-etag,new-type,new-body"


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_hit_not_modified(
    repository: CachedHttpRepository,
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
    httpx_mock.add_response(status_code=304)

    repository._save_to_cache("http://url", "stored-etag,stored-type,stored-body")
    body, content_type = await repository._fetch_simple_page("http://url")
    assert body == "stored-body"
    assert content_type == "stored-type"


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_hit_modified(
    repository: CachedHttpRepository,
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
    httpx_mock.add_response(
        content="new-body",
        headers={
            "Content-Type": "new-type",
            "ETag": "new-etag",
        },
    )
    repository._save_to_cache("http://url", "stored-etag,stored-type,stored-body")
    body, content_type = await repository._fetch_simple_page("http://url")
    assert body == "new-body"
    assert content_type == "new-type"
    assert repository._get_from_cache("http://url") == "new-etag,new-type,new-body"


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_hit_source_unreachable(
    repository: CachedHttpRepository,
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
    repository._save_to_cache("url", "stored-etag,stored-type,stored-body")
    httpx_mock.add_exception(httpx.RequestError("error"))
    body, content_type = await repository._fetch_simple_page("url")
    assert body == "stored-body"
    assert content_type == "stored-type"
    assert repository._get_from_cache("url") == "stored-etag,stored-type,stored-body"


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_miss_source_unreachable(
    repository: CachedHttpRepository,
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
    httpx_mock.add_exception(httpx.RequestError("error"))
    with pytest.raises(httpx.RequestError, match="error"):
        await repository._fetch_simple_page("url")


@pytest.mark.asyncio
async def test_get_project_page__cached(
    repository: CachedHttpRepository,
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
    repository._save_to_cache(
        "https://example.com/simple/project/",
        "stored-etag,text/html,"
        + """
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
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
    repository._save_to_cache(
        "https://example.com/simple/",
        "stored-etag,text/html,"
        + """
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
        projects=frozenset(
            [
                model.ProjectListElement(name="p1"),
                model.ProjectListElement(name="p2"),
            ],
        ),
    )


def test_update_access_time(repository: CachedHttpRepository) -> None:
    repository._save_to_cache("url", "content")
    with mock.patch(
        "simple_repository.components.http_cached.datetime",
        mock.Mock(
            now=mock.Mock(return_value=datetime.fromisoformat("2006-07-09")),
            fromisoformat=datetime.fromisoformat,
            spec=datetime,
        ),
    ):
        repository._get_from_cache("url")

    assert (
        os.path.getmtime(repository._cache_path / "url")
        == datetime.fromisoformat("2006-07-09").timestamp()
    )
