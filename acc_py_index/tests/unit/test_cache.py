import pathlib
import sqlite3
from unittest import mock

import pytest

from acc_py_index.cache import TTLDatabaseCache


@pytest.fixture
def cache(tmp_path: pathlib.PosixPath) -> TTLDatabaseCache:
    db = sqlite3.connect(tmp_path / "test.db")
    return TTLDatabaseCache(db, 5, "my_table")


def test_get_set(cache: TTLDatabaseCache) -> None:
    assert cache.get("pizza") is None

    cache.set("pizza", "margherita")
    assert cache.get("pizza") == "margherita"

    cache.set("pizza", "salame")
    assert cache.get("pizza") == "salame"


def test_multi_set(cache: TTLDatabaseCache) -> None:
    assert cache.get("pizza") is None
    assert cache.get("pasta") is None

    cache.set({"pizza": "margherita", "pasta": "carbonara"})

    assert cache.get("pizza") == "margherita"
    assert cache.get("pasta") == "carbonara"


def test_ttl(cache: TTLDatabaseCache) -> None:
    cache.ttl = 0
    cache.set("pizza", "margherita")
    res = cache._database.execute(
        "SELECT value FROM my_table WHERE key = 'pizza'",
    ).fetchone()
    assert res[0] == "margherita"

    assert cache.get("pizza") is None

    cache.set("pasta", "carbonara")
    res = cache._database.execute(
        "SELECT value FROM my_table WHERE key = 'pizza'",
    ).fetchone()
    assert res is None


def test_subscriptions(cache: TTLDatabaseCache) -> None:
    with pytest.raises(KeyError):
        cache["pizza"]
    cache["pizza"] = "margherita"
    assert cache["pizza"] == "margherita"


def test_invalid_name() -> None:
    with pytest.raises(
        ValueError,
        match="Table names must only contain letters, digits, and underscores.",
    ):
        TTLDatabaseCache(mock.Mock(), 5, "passwords--")
