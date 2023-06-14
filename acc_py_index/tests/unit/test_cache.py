import pathlib
import sqlite3
from unittest import mock

import pytest

from acc_py_index.ttl_cache import TTLDatabaseCache


@pytest.fixture
def cache(tmp_path: pathlib.PosixPath) -> TTLDatabaseCache:
    db = sqlite3.connect(tmp_path / "test.db")
    return TTLDatabaseCache(db, 5, "my_table")


def test_get_set(cache: TTLDatabaseCache) -> None:
    assert cache.get("pizza") is None
    assert cache.get("pizza", "") == ""

    with pytest.raises(KeyError, match="pizza"):
        cache["pizza"]

    cache["pizza"] = "margherita"
    assert cache.get("pizza") == "margherita"

    cache["pizza"] = "salame"
    assert cache.get("pizza") == "salame"


def test_update(cache: TTLDatabaseCache) -> None:
    assert cache.get("pizza") is None
    assert cache.get("pasta") is None

    cache.update({"pizza": "margherita", "pasta": "carbonara"})

    assert cache.get("pizza") == "margherita"
    assert cache.get("pasta") == "carbonara"


def test_ttl(cache: TTLDatabaseCache) -> None:
    cache.ttl = 0
    cache["pizza"] = "margherita"
    res = cache._database.execute(
        "SELECT value FROM my_table WHERE key = 'pizza'",
    ).fetchone()
    assert res[0] == "margherita"

    assert cache.get("pizza") is None

    cache["pasta"] = "carbonara"
    res = cache._database.execute(
        "SELECT value FROM my_table WHERE key = 'pizza'",
    ).fetchone()
    assert res is None


def test_contains(cache: TTLDatabaseCache) -> None:
    assert ("pizza" in cache) is False
    cache["pizza"] = "margherita"
    assert ("pizza" in cache) is True


def test_invalid_name() -> None:
    with pytest.raises(
        ValueError,
        match="Table names must only contain letters, digits, and underscores.",
    ):
        TTLDatabaseCache(mock.Mock(), 5, "passwords--")
