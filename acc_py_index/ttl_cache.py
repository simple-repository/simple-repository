import datetime
import logging
import re
import sqlite3
from typing import Optional

TABLE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]+$')

error_logger = logging.getLogger("gunicorn.error")


class TTLDatabaseCache:
    """Time-to-Live (TTL) cache that stores key-value
    string pairs in an SQLite database.
    """
    def __init__(
        self,
        database: sqlite3.Connection,
        ttl_seconds: int,
        table_name: str = "data",
    ) -> None:
        self._database = database

        if TABLE_NAME_PATTERN.match(table_name) is None:
            raise ValueError(
                "Table names must only contain "
                "letters, digits, and underscores.",
            )

        database.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name}"
            "(key TEXT, value TEXT, valid_until TIMESTAMP"
            ", CONSTRAINT pk PRIMARY KEY (key))",
        )
        self.table_name = table_name
        self.ttl = ttl_seconds

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        now = datetime.datetime.now()

        try:
            res: Optional[tuple[str]] = self._database.execute(
                f'''SELECT value FROM {self.table_name}
                WHERE key = :key AND valid_until > :now''',
                {"key": key, "now": now},
            ).fetchone()
        except sqlite3.DatabaseError:
            # If the query fails because the database
            # is locked, assume a cache miss.
            res = None

        if res is not None:
            return res[0]
        return default

    def update(self, data: dict[str, str]) -> None:
        now = datetime.datetime.now()
        valid_until = now + datetime.timedelta(seconds=self.ttl)
        query_params = [
            {"key": key, "value": val, "valid_until": valid_until}
            for key, val in data.items()
        ]
        try:
            self._database.execute(
                f"DELETE FROM {self.table_name} WHERE valid_until < :now",
                {"now": now},
            )
            self._database.executemany(
                f'''INSERT INTO {self.table_name} (key, value, valid_until)
                VALUES (:key, :value, :valid_until) ON
                CONFLICT(key) DO UPDATE SET value=excluded.value,
                valid_until=excluded.valid_until''',
                query_params,
            )
            self._database.commit()
        except sqlite3.DatabaseError:
            # If the query fails because the database
            # is locked, don't cache the new values.
            pass

    def __getitem__(self, key: object) -> str:
        if not isinstance(key, str):
            raise TypeError("Key must be a string")
        val = self.get(key)
        if val is not None:
            return val
        raise KeyError(key)

    def __setitem__(self, key: object, value: str) -> None:
        if not isinstance(key, str):
            raise TypeError("Key must be a string")
        self.update({key: value})

    def __contains__(self, value: object) -> bool:
        if not isinstance(value, str):
            raise TypeError("Value must be a string")
        return self.get(value) is not None
