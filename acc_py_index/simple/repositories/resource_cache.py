import datetime
import pathlib
import sqlite3
from typing import Optional
import uuid

import aiohttp

from ... import utils
from ...ttl_cache import TABLE_NAME_PATTERN
from ..model import HttpResource, LocalResource, Resource
from .core import RepositoryContainer, SimpleRepository


class ResourceCacheRepository(RepositoryContainer):
    """
    A cache for remote resources. It stores temporarily remote
    resources on the local disk, allowing faster access and
    mitigating the effects of source repository downtime.
    """
    def __init__(
        self,
        source: SimpleRepository,
        cache_path: pathlib.Path,
        session: aiohttp.ClientSession,
        database: sqlite3.Connection,
        table_name: str = "resource_cache_data",
    ) -> None:
        super().__init__(source)
        self._cache_path = cache_path.resolve()
        self._tmp_path = self._cache_path / ".incomplete"
        self._tmp_path.mkdir(parents=True, exist_ok=True)
        self._session = session
        self._database = database
        self._table_name = table_name

        self._init_database()

    async def get_resource(self, project_name: str, resource_name: str) -> Resource:
        """
        Get a resource from the cache. If it is not present in the
        cache, retrieve it from the source repository. If it's a
        remote resource, download the resource and cache it.
        """
        resource_path = (self._cache_path / resource_name).resolve()

        # Ensures that the requested resource is contained
        # in the cache directory to avoid path traversal.
        if not resource_path.is_relative_to(self._cache_path):
            raise ValueError(f"{resource_path} is not contained in {self._cache_path}")

        cached_resource = LocalResource(path=resource_path)
        # If the package is currently cached, return it.
        # Currently no cache invalidation mechanism is provided
        # for packages that are assumed to be immutable.
        if resource_path.is_file():
            self._update_last_access_for(f"{project_name}/{resource_name}")
            return cached_resource

        resource = await super().get_resource(project_name, resource_name)

        # If the upstream resource is a REMOTE_RESOURCE, download and
        # cache it. Then return a local resource pointing to that file.
        if isinstance(resource, HttpResource):
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            dest_file = self._tmp_path / f"{timestamp}_{uuid.uuid4().hex}"
            await utils.download_file(
                download_url=resource.url,
                dest_file=dest_file,
                session=self._session,
            )
            dest_file.rename(resource_path)
            self._update_last_access_for(f"{project_name}/{resource_name}")
            return cached_resource

        return resource

    def _init_database(self) -> None:
        if TABLE_NAME_PATTERN.match(self._table_name) is None:
            raise ValueError(
                "Table names must only contain "
                "letters, digits, and underscores.",
            )
        self._database.execute(
            f"CREATE TABLE IF NOT EXISTS {self._table_name}"
            "(resource TEXT, last_access TIMESTAMP"
            ", CONSTRAINT pk PRIMARY KEY (resource))",
        )

    def _update_last_access_for(self, resource: str) -> None:
        today = datetime.datetime.now()
        res: Optional[tuple[str]] = self._database.execute(
            f'''SELECT last_access FROM {self._table_name}
            WHERE resource = :resource''',
            {"resource": resource},
        ).fetchone()

        # To reduce the number of writes, we only update this
        # if more than a day since the last_access has passe.
        if not res or (today - datetime.datetime.fromisoformat(res[0])).days > 1:
            self._database.execute(
                f'''INSERT INTO {self._table_name} (resource, last_access)
                VALUES (:resource, :last_access) ON
                CONFLICT(resource) DO UPDATE SET
                last_access=excluded.last_access''',
                {"resource": resource, "last_access": today},
            )
            self._database.commit()
