import datetime
import os
import pathlib
import uuid

import aiohttp

from ... import utils
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
    ) -> None:
        super().__init__(source)
        self._cache_path = cache_path.resolve()
        self._tmp_path = self._cache_path / ".incomplete"
        self._tmp_path.mkdir(parents=True, exist_ok=True)
        self._session = session

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
            self._update_last_access_for(resource_path)
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
            self._update_last_access_for(resource_path)
            return cached_resource

        return resource

    def _update_last_access_for(self, resource_path: pathlib.Path) -> None:
        """
        Store the last access as the access and modified times of the file.
        That information will be used to delete unused files in the cache.
        """
        now = datetime.datetime.now().timestamp()
        os.utime(resource_path, (now, now))
