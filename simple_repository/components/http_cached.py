# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import os
import pathlib
import typing
import urllib.parse
import uuid

import httpx

from . import http

error_logger = logging.getLogger("gunicorn.error")


class CachedHttpRepository(http.HttpRepository):
    """
    Caches the http responses received from the source,
    manages cache invalidation using ETAGS.
    If the source is unavailable, will return, if available,
    cached elements (even if stale).
    """

    def __init__(
        self,
        url: str,
        cache_path: pathlib.Path,
        http_client: typing.Optional[httpx.AsyncClient] = None,
        connection_timeout: timedelta = timedelta(seconds=15),
    ) -> None:
        super().__init__(url, http_client, connection_timeout)
        self._cache_path = cache_path.resolve()
        self._tmp_dir = cache_path / ".incomplete"
        self._tmp_dir.mkdir(parents=True, exist_ok=True)

    def _get_from_cache(self, page_url: str) -> typing.Optional[str]:
        cached_resource_path = self._cache_path / urllib.parse.quote_plus(page_url)
        if not cached_resource_path.is_file():
            return None
        now = datetime.now().timestamp()
        # Depending on the OS configuration, atime modification
        # on read may be disabled, so we set it explicitly.
        os.utime(cached_resource_path, (now, now))
        return cached_resource_path.read_text()

    def _save_to_cache(self, page_url: str, content: str) -> None:
        cached_resource_path = self._cache_path / urllib.parse.quote_plus(page_url)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        dest_file = self._tmp_dir / f"{timestamp}_{uuid.uuid4().hex}"
        dest_file.write_text(content)
        # Use rename atomicity to avoid set/get race conditions
        dest_file.rename(cached_resource_path)

    async def _fetch_simple_page(
        self,
        page_url: str,
    ) -> typing.Tuple[str, str]:
        """Retrieves a simple page from the given URL. The retrieved page,
        content type and etag are cached. If the cached content is
        unchanged or the source is unavailable, the cached data is returned.
        """
        headers = {"Accept": self.downstream_content_types}

        cached_content = self._get_from_cache(page_url)
        if cached_content:
            etag, cached_content_type, cached_page = cached_content.split(",", 2)
            headers.update({"If-None-Match": etag})

        try:
            response = await self._http_client.get(
                url=page_url,
                headers=headers,
                timeout=self._connection_timeout.total_seconds(),
            )
        except httpx.HTTPError as e:
            # If the connection to the source fails, and there is a cached page for
            # the requested URL, return the cached content, otherwise raise the error.
            error_logger.error(
                f"Connection to {page_url} failed with the following error: {str(e)}",
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
        new_etag = response.headers.get("ETag", "")
        if new_etag:
            # If the ETag is set, cache the response for future use.
            self._save_to_cache(page_url, ",".join([new_etag, content_type, body]))
        return body, content_type
