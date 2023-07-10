import pathlib
import sqlite3
import typing
from unittest import mock

import aiohttp
import pytest

from acc_py_index.simple import model
from acc_py_index.simple.repositories.http_cached import CachedHttpRepository


@pytest.fixture
def repository(
    tmp_path: pathlib.Path,
) -> typing.Generator[CachedHttpRepository, None, None]:
    try:
        db_connection = sqlite3.connect(tmp_path / "tmp.db")
        repo = CachedHttpRepository(
            url="https://example.com/simple/",
            session=mock.MagicMock(),
            database=db_connection,
        )
        yield repo
    finally:
        db_connection.close()


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
    repository.session.get.return_value.__aenter__.return_value = response_mock

    body, content_type = await repository._fetch_simple_page("url")
    assert body == "new-body"
    assert content_type == "new-type"
    response_mock.raise_for_status.assert_called_once()

    cached = repository._cache["url"]
    assert cached == "new-etag,new-type,new-body"


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_hit_not_modified(
    repository: CachedHttpRepository,
    response_mock: mock.AsyncMock,
) -> None:
    repository._cache["url"] = "stored-etag,stored-type,stored-body"
    response_mock.status = 304
    repository.session.get.return_value.__aenter__.return_value = response_mock
    body, content_type = await repository._fetch_simple_page("url")
    assert body == "stored-body"
    assert content_type == "stored-type"


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_hit_modified(
    repository: CachedHttpRepository,
    response_mock: mock.AsyncMock,
) -> None:
    repository._cache["url"] = "stored-etag,stored-type,stored-body"
    repository.session.get.return_value.__aenter__.return_value = response_mock
    body, content_type = await repository._fetch_simple_page("url")
    assert body == "new-body"
    assert content_type == "new-type"
    assert repository._cache["url"] == "new-etag,new-type,new-body"


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_hit_source_unreachable(
    repository: CachedHttpRepository,
) -> None:
    repository._cache["url"] = "stored-etag,stored-type,stored-body"
    repository.session.get.return_value.__aenter__.side_effect = aiohttp.ClientConnectionError()
    body, content_type = await repository._fetch_simple_page("url")
    assert body == "stored-body"
    assert content_type == "stored-type"
    assert repository._cache["url"] == "stored-etag,stored-type,stored-body"


@pytest.mark.asyncio
async def test_fetch_simple_page__cache_miss_source_unreachable(
    repository: CachedHttpRepository,
) -> None:
    repository.session.get.return_value.__aenter__.side_effect = aiohttp.ClientConnectionError()
    with pytest.raises(aiohttp.ClientConnectionError):
        await repository._fetch_simple_page("url")


@pytest.mark.asyncio
async def test_get_project_page__cached(
    repository: CachedHttpRepository,
    response_mock: mock.AsyncMock,
) -> None:
    repository._cache["https://example.com/simple/project/"] = "stored-etag,text/html," + """
        <a href="test1.whl#hash=test_hash">test1.whl</a>
        <a href="http://test2.whl">test2.whl</a>
    """
    response_mock.status = 304
    repository.session.get.return_value.__aenter__.return_value = response_mock
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
    repository._cache["https://example.com/simple/"] = "stored-etag,text/html," + """
        <a href="/p1/">p1</a>
        <a href="/p2/">p2</a>
    """
    response_mock.status = 304
    repository.session.get.return_value.__aenter__.return_value = response_mock
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
