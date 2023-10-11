# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import pathlib
import typing
from unittest import mock

import aiosqlite
import pytest
import pytest_asyncio

from ..ttl_cache import TTLDatabaseCache


@pytest_asyncio.fixture
async def cache(
    tmp_path: pathlib.PosixPath,
) -> typing.AsyncGenerator[TTLDatabaseCache, None]:
    async with aiosqlite.connect(tmp_path / "test.db") as db:
        yield TTLDatabaseCache(db, 5, "my_table")


@pytest.mark.asyncio
async def test_get_set(cache: TTLDatabaseCache) -> None:
    assert await cache.get("pizza") is None
    assert await cache.get("pizza", "") == ""

    await cache.set("pizza", "margherita")
    assert await cache.get("pizza") == "margherita"

    await cache.set("pizza", "salame")
    assert await cache.get("pizza") == "salame"


@pytest.mark.asyncio
async def test_update(cache: TTLDatabaseCache) -> None:
    assert await cache.get("pizza") is None
    assert await cache.get("pasta") is None

    await cache.update({"pizza": "margherita", "pasta": "carbonara"})

    assert await cache.get("pizza") == "margherita"
    assert await cache.get("pasta") == "carbonara"


@pytest.mark.asyncio
async def test_ttl(cache: TTLDatabaseCache) -> None:
    cache.ttl = 0
    await cache.set("pizza", "margherita")
    async with cache._database.execute(
        "SELECT value FROM my_table WHERE key = 'pizza'",
    ) as cur:
        res = await cur.fetchone()
    assert res[0] == "margherita"
    assert await cache.get("pizza") is None

    await cache.set("pasta", "carbonara")
    async with cache._database.execute(
        "SELECT value FROM my_table WHERE key = 'pizza'",
    ) as cur:
        res = await cur.fetchone()
    assert res is None


def test_invalid_name() -> None:
    with pytest.raises(
        ValueError,
        match="Table names must only contain letters, digits, and underscores.",
    ):
        TTLDatabaseCache(mock.Mock(), 5, "passwords--")


@pytest.mark.asyncio
async def test_get__database_error(cache: TTLDatabaseCache) -> None:
    database_mock = mock.AsyncMock(spec=aiosqlite.Connection)
    database_mock.execute.side_effect = aiosqlite.DatabaseError()
    cache._database = database_mock

    assert await cache.get("anything") is None


@pytest.mark.asyncio
async def test_update__database_error(cache: TTLDatabaseCache) -> None:
    database_mock = mock.Mock(spec=aiosqlite.Connection)
    database_mock.execute.side_effect = aiosqlite.DatabaseError()
    cache._database = database_mock

    await cache.update({"anything": "anywhere"})
