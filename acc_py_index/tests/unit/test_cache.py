import pathlib
import sqlite3

import pytest

from acc_py_index.cache import TTLCache


@pytest.fixture
def cache(tmp_path: pathlib.PosixPath) -> TTLCache:
    db = sqlite3.connect(tmp_path / "test.db")
    return TTLCache(db, 5, "my_table")


def test_get_set(cache: TTLCache) -> None:
    assert cache.get("pizza") is None

    cache.set("pizza", "margherita")
    assert cache.get("pizza") == "margherita"

    cache.set("pizza", "salame")
    assert cache.get("pizza") == "salame"


def test_mset(cache: TTLCache) -> None:
    assert cache.get("pizza") is None
    assert cache.get("pasta") is None

    cache.mset({"pizza": "margherita", "pasta": "carbonara"})

    assert cache.get("pizza") == "margherita"
    assert cache.get("pasta") == "carbonara"


def test_ttl(cache: TTLCache) -> None:
    cache.ttl = 0
    cache.set("pizza", "margherita")
    res = cache.database.execute(
        "SELECT value FROM my_table WHERE key = 'pizza'",
    ).fetchone()
    assert res[0] == "margherita"

    assert cache.get("pizza") is None

    cache.set("pasta", "carbonara")
    res = cache.database.execute(
        "SELECT value FROM my_table WHERE key = 'pizza'",
    ).fetchone()
    assert res is None


def test_square_brackets(cache: TTLCache) -> None:
    with pytest.raises(KeyError):
        cache["pizza"]
    cache["pizza"] = "margherita"
    assert cache["pizza"] == "margherita"
