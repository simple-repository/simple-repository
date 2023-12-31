# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import logging

import aiosqlite
import httpx

from ..ttl_cache import TTLDatabaseCache
from .http import HttpRepository

error_logger = logging.getLogger("gunicorn.error")


class CachedHttpRepository(HttpRepository):
    """
    Caches the http responses received from the source,
    manages cache invalidation using ETAGS.
    If the source is unavailable, will return, if available,
    cached elements (even if stale).
    The TTL is used to clear the cache of unused records.
    The TTL for a cached item is updated after each
    access to that element. Expired items are removed from the
    from the cache. Items within their TTL are still validated using
    etags, and replaced if upstream has updated.
    """

    def __init__(
        self,
        url: str,
        database: aiosqlite.Connection,
        http_client: httpx.AsyncClient | None = None,
        table_name: str = "simple_repository_cache",
        # Cached pages (even if still valid) will
        # be deleted after 7 days if not accessed
        ttl_seconds: int = 60 * 60 * 24 * 7,
        connection_timeout_seconds: int = 15,
    ):
        super().__init__(url, http_client)
        self._cache = TTLDatabaseCache(database, ttl_seconds, table_name)
        self._connection_timeout_seconds = connection_timeout_seconds

    async def _fetch_simple_page(
        self,
        page_url: str,
    ) -> tuple[str, str]:
        """Retrieves a simple page from the given URL. The retrieved page,
        content type and etag are cached. If the cached content is
        unchanged or the source is unavailable, the cached data is returned.
        """
        headers = {"Accept": self.downstream_content_types}

        if cached_content := await self._cache.get(page_url):
            etag, cached_content_type, cached_page = cached_content.split(",", 2)
            headers.update({"If-None-Match": etag})

        try:
            response = await self._http_client.get(
                url=page_url,
                headers=headers,
                timeout=self._connection_timeout_seconds,
            )
        except (httpx.TimeoutException, httpx.RequestError) as e:
            # If the connection to the source fails, and there is a cached page for
            # the requested URL, return the cached content, otherwise raise the error.
            error_logger.error(
                f"Connection to {page_url} failed with"
                f" the following error: {str(e)}",
            )
            if cached_content:
                return cached_page, cached_content_type
            raise

        if response.status_code == 304 and cached_content:
            # The cached content is still valid.
            return cached_page, cached_content_type

        response.raise_for_status()

        body = response.text
        content_type = response.headers.get("Content-Type", "")
        if new_etag := response.headers.get("ETag", ""):
            # If the ETag is set, cache the response for future use.
            await self._cache.set(page_url, ",".join([new_etag, content_type, body]))
        return body, content_type
