# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import datetime
import os
import pathlib
import uuid

import aiohttp

from .. import model, utils
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

    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.Resource:
        """
        Get a resource from the cache. If it is not present in the
        cache, retrieve it from the source repository. If it's a
        remote resource, download the resource and cache it.
        """
        project_dir = (self._cache_path / project_name).resolve()
        resource_path = (project_dir / resource_name).resolve()
        resource_info_path = resource_path.with_suffix(resource_path.suffix + ".info")

        # Ensures that the requested resource is contained
        # in the cache directory to avoid path traversal.
        if (
            not resource_path.is_relative_to(self._cache_path) or
            not project_dir.is_relative_to(self._cache_path)
        ):
            raise ValueError(f"{resource_path} is not contained in {self._cache_path}")

        project_dir.mkdir(exist_ok=True)

        cache_etag = resource_info_path.read_text() if resource_info_path.is_file() else None
        resource = await super().get_resource(
            project_name,
            resource_name,
            request_context=request_context,
        )
        upstream_etag = resource.context.get("etag")
        if not isinstance(resource, model.HttpResource) or not upstream_etag:
            # Only cache HttpResources if the source repo sets an etag.
            return resource

        if upstream_etag != cache_etag:
            # The upstream resource changed or no cached version is available.
            # Fetch the resource and cache it and its etag.
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            dest_file = self._tmp_path / f"{timestamp}_{uuid.uuid4().hex}"
            await utils.download_file(
                download_url=resource.url,
                dest_file=dest_file,
                session=self._session,
            )
            dest_file.rename(resource_path)
            resource_info_path.write_text(upstream_etag)

        self._update_last_access(resource_info_path)

        local_resource = model.LocalResource(path=resource_path)
        local_resource.context.update(resource.context)

        return local_resource

    def _update_last_access(
        self,
        resource_info_path: pathlib.Path,
    ) -> None:
        """
        Store the last access as the access and modified times of the file.
        That information will be used to delete unused files in the cache.
        """
        now = datetime.datetime.now().timestamp()

        os.utime(resource_info_path, (now, now))
