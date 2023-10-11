# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import datetime
import logging
import re
import sqlite3
from typing import Optional

import aiosqlite

TABLE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]+$')

error_logger = logging.getLogger("gunicorn.error")


class TTLDatabaseCache:
    """Time-to-Live (TTL) cache that stores key-value
    string pairs in an SQLite database.
    """
    def __init__(
        self,
        database: aiosqlite.Connection,
        ttl_seconds: int,
        table_name: str = "data",
    ) -> None:
        self._database = database

        if TABLE_NAME_PATTERN.match(table_name) is None:
            raise ValueError(
                "Table names must only contain "
                "letters, digits, and underscores.",
            )
        # TODO: Use a synchronization mechanism instead.
        self._initialise_db = True
        self.table_name = table_name
        self.ttl = ttl_seconds

    async def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        await self._init_db()

        now = datetime.datetime.now()
        try:
            async with self._database.execute(
                f'''SELECT value FROM {self.table_name}
                WHERE key = :key AND valid_until > :now''',
                {"key": key, "now": now},
            ) as cur:
                res = await cur.fetchone()
        except (aiosqlite.DatabaseError, sqlite3.InterfaceError):
            # If the query fails because the database
            # is locked, assume a cache miss.
            res = None

        if res is not None:
            result = res[0]
            assert isinstance(result, str)
            return result
        return default

    async def update(self, data: dict[str, str]) -> None:
        await self._init_db()

        now = datetime.datetime.now()
        valid_until = now + datetime.timedelta(seconds=self.ttl)
        query_params = [
            {"key": key, "value": val, "valid_until": valid_until}
            for key, val in data.items()
        ]
        try:
            await self._database.execute(
                f"DELETE FROM {self.table_name} WHERE valid_until < :now",
                {"now": now},
            )
            await self._database.executemany(
                f'''INSERT INTO {self.table_name} (key, value, valid_until)
                VALUES (:key, :value, :valid_until) ON
                CONFLICT(key) DO UPDATE SET value=excluded.value,
                valid_until=excluded.valid_until''',
                query_params,
            )
            await self._database.commit()
        except (aiosqlite.DatabaseError, sqlite3.InterfaceError):
            # If the query fails because the database
            # is locked, don't cache the new values.
            pass

    async def set(self, key: str, value: str) -> None:
        await self.update({key: value})

    async def _init_db(self) -> None:
        if not self._initialise_db:
            return

        try:
            await self._database.execute(
                f"CREATE TABLE IF NOT EXISTS {self.table_name}"
                "(key TEXT, value TEXT, valid_until TIMESTAMP"
                ", CONSTRAINT pk PRIMARY KEY (key))",
            )
        except (aiosqlite.DatabaseError, sqlite3.InterfaceError):
            # If the query fails because the database
            # is locked, postpone the init.
            return

        self._initialise_db = False
