# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

from datetime import datetime
import logging
import os
import pathlib
import shutil
import typing
import uuid

import httpx

from .. import errors, model, utils
from .._typing_compat import override
from . import core


class ResourceCacheRepository(core.RepositoryContainer):
    """
    A cache for resources based on etags. It stores temporarily
    resources with an assigned etag on the local disk.
    When fallback_to_cache is enabled (default), then a cached resource
    will be returned if the source repository is unavailable. Used in
    the right context, this can be used for example to maintain a functional
    repository for previously seen responses when PyPI.org is down.
    """

    def __init__(
        self,
        source: core.SimpleRepository,
        cache_path: pathlib.Path,
        http_client: typing.Optional[httpx.AsyncClient] = None,
        logger: logging.Logger = logging.getLogger(__name__),
        fallback_to_cache: bool = True,
    ) -> None:
        super().__init__(source)
        self._cache_path = cache_path.resolve()
        self._tmp_path = self._cache_path / ".incomplete"
        self._tmp_path.mkdir(parents=True, exist_ok=True)
        self._http_client = http_client or httpx.AsyncClient()
        self._logger = logger
        self._fallback_to_cache = fallback_to_cache

    @override
    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.Resource:
        """
        Get a resource from the cache. If it is not present in the
        cache, or its etag has expired, retrieve it from the source repository.
        If it's a remote resource, download the resource and cache it.
        """
        request_context = request_context or model.RequestContext()

        project_dir = (self._cache_path / project_name).resolve()
        resource_path = (project_dir / resource_name).resolve()
        resource_info_path = resource_path.with_suffix(resource_path.suffix + ".info")

        # Ensures that the requested resource is contained
        # in the cache directory to avoid path traversal.
        if not utils.is_relative_to(
            resource_path,
            self._cache_path,
        ) or not utils.is_relative_to(project_dir, self._cache_path):
            raise ValueError(f"{resource_path} is not contained in {self._cache_path}")

        project_dir.mkdir(exist_ok=True)

        # Require the resource upstream, if available use the cached etag.
        cache_etag = (
            resource_info_path.read_text() if resource_info_path.is_file() else None
        )
        if cache_etag:
            context: typing.Mapping[str, typing.Any] = {
                **request_context.context,
                "etag": cache_etag,
            }
        else:
            context = request_context.context
        new_request_context = model.RequestContext(
            context=context,
        )
        try:
            resource = await super().get_resource(
                project_name,
                resource_name,
                request_context=new_request_context,
            )
        except model.NotModified:
            # The upstream repository serves the same content that has been cached.
            # If the request also provides the same etag, raise NotModified,
            # otherwise return the locally cached resource.
            if cache_etag == request_context.context.get("etag"):
                raise
            return self._cached_resource(
                resource_path=resource_path,
                resource_info_path=resource_info_path,
                context=model.Context(etag=cache_etag)
                if cache_etag
                else model.Context(),
            )
        except errors.SourceRepositoryUnavailable:
            if not self._fallback_to_cache:
                raise
            # If the source repository behaves incorrectly and we
            # have a cached artifact, return it to the client.
            self._logger.error(
                f"Upstream unavailable, served cached {project_name}:{resource_name}",
            )
            if cache_etag:
                return self._cached_resource(
                    resource_path=resource_path,
                    resource_info_path=resource_info_path,
                    context=model.Context(etag=cache_etag),
                )
            else:
                raise

        upstream_etag = resource.context.get("etag")
        if not upstream_etag or resource.to_cache is False:
            # Only cache a resource if has an etag and to_cache is set to True.
            return resource

        if upstream_etag != cache_etag:
            await self._store_resource(
                resource=resource,
                upstream_etag=upstream_etag,
                resource_path=resource_path,
                resource_info_path=resource_info_path,
            )

        return self._cached_resource(
            resource_path=resource_path,
            resource_info_path=resource_info_path,
            context=resource.context,
        )

    async def _store_resource(
        self,
        resource: model.Resource,
        upstream_etag: str,
        resource_path: pathlib.Path,
        resource_info_path: pathlib.Path,
    ) -> None:
        if isinstance(resource, model.HttpResource):
            # The upstream resource changed or no cached version is available.
            # Fetch the resource and cache it and its etag.
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            dest_file = self._tmp_path / f"{timestamp}_{uuid.uuid4().hex}"
            await utils.download_file(
                download_url=resource.url,
                dest_file=dest_file,
                http_client=self._http_client,
            )
            dest_file.rename(resource_path)
        elif isinstance(resource, model.TextResource):
            resource_path.write_text(resource.text)
        elif isinstance(resource, model.LocalResource):
            shutil.copy(resource.path, resource_path)
        else:
            raise ValueError(f"Unknown resource type: {type(resource)}.")
        resource_info_path.write_text(upstream_etag)

    def _cached_resource(
        self,
        resource_path: pathlib.Path,
        resource_info_path: pathlib.Path,
        context: model.Context,
    ) -> model.LocalResource:
        self._update_last_access(resource_info_path)
        local_resource = model.LocalResource(path=resource_path)
        local_resource.context.update(context)
        return local_resource

    def _update_last_access(
        self,
        resource_info_path: pathlib.Path,
    ) -> None:
        """
        Store the last access as the access and modified times of the file.
        That information will be used to delete unused files in the cache.
        """
        now = datetime.now().timestamp()

        os.utime(resource_info_path, (now, now))
