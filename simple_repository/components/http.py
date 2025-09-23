# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import dataclasses
from datetime import timedelta
import typing
from urllib.parse import urlsplit, urlunsplit

import httpx

from .. import errors, model, parser, utils
from .._typing_compat import override
from . import core


def _url_path_append(url: str, append_with: str) -> str:
    """
    Append to the path part of the URL, taking care of trailing slashes on
    the root_url. `append_with` may contain sub-paths, and may end with a
    slash if desired.

    """
    PATH_IDX = 2

    split_url = list(urlsplit(url))

    if not split_url[PATH_IDX].endswith("/"):
        # Add a trailing slash to the path.
        split_url[PATH_IDX] += "/"

    if append_with.startswith("/"):
        append_with = append_with[1:]

    split_url[PATH_IDX] += append_with
    new_url = urlunsplit(split_url)
    return new_url


class HttpRepository(core.SimpleRepository):
    """Proxy of a remote simple repository

    By default, creates an HTTP client that follows redirects. When providing
    a custom http_client, it's recommended to configure it with
    `follow_redirects=True` to handle cases where repository servers redirect
    requests.
    """

    def __init__(
        self,
        url: str,
        http_client: typing.Optional[httpx.AsyncClient] = None,
        connection_timeout: timedelta = timedelta(seconds=15),
    ) -> None:
        self._source_url = url
        self._http_client = http_client or httpx.AsyncClient(follow_redirects=True)
        self.downstream_content_types = ", ".join(
            [
                "application/vnd.pypi.simple.v1+json",
                "application/vnd.pypi.simple.v1+html;q=0.2",
                "text/html;q=0.01",
            ],
        )
        self._connection_timeout = connection_timeout

    async def _fetch_simple_page(
        self,
        page_url: str,
    ) -> typing.Tuple[str, str]:
        """Retrieves a simple page from the given url.
        Returns the body and the content type received.
        """
        headers = {"Accept": self.downstream_content_types}
        response = await self._http_client.get(
            url=page_url,
            headers=headers,
            timeout=self._connection_timeout.total_seconds(),
        )
        response.raise_for_status()
        body = response.text
        content_type: str = response.headers.get("content-type", "")
        return body, content_type

    @override
    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.ProjectDetail:
        page_url = _url_path_append(self._source_url, f"{project_name}/")
        try:
            body, content_type = await self._fetch_simple_page(page_url)
        except httpx.HTTPError as e:
            # If the status_code is 404, the source repository is working correctly, but
            # the requested resource is not available. Any other 4xx or 5xx error code is
            # treated as a source repository misbehaviour
            if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 404:
                raise errors.PackageNotFoundError(
                    package_name=project_name,
                ) from e
            # This code path also includes connection failures or timeouts.
            raise errors.SourceRepositoryUnavailable() from e

        if (
            "application/vnd.pypi.simple.v1+html" in content_type
            or "text/html" in content_type
            or not content_type
        ):
            project_page = parser.parse_html_project_page(body, project_name)
        elif "application/vnd.pypi.simple.v1+json" in content_type:
            project_page = parser.parse_json_project_page(body)
        else:
            raise errors.UnsupportedSerialization(content_type)

        # Make the URLs in the project page absolute, such that they can be
        # resolved upstream without knowing the original source URLs.
        files = tuple(
            dataclasses.replace(file, url=utils.url_absolutizer(file.url, page_url))
            for file in project_page.files
        )
        project_page = dataclasses.replace(project_page, files=files)
        return project_page

    @override
    async def get_project_list(
        self,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.ProjectList:
        try:
            body, content_type = await self._fetch_simple_page(self._source_url)
        except httpx.HTTPError as e:
            raise errors.SourceRepositoryUnavailable() from e

        if (
            "application/vnd.pypi.simple.v1+html" in content_type
            or "text/html" in content_type
            or not content_type
        ):
            return parser.parse_html_project_list(body)
        elif "application/vnd.pypi.simple.v1+json" in content_type:
            return parser.parse_json_project_list(body)

        raise errors.UnsupportedSerialization(content_type)

    @override
    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.Resource:
        request_context = request_context or model.RequestContext()
        try:
            project_page = await self.get_project_page(
                project_name,
                request_context=request_context,
            )
        except errors.PackageNotFoundError:
            raise

        resource: typing.Optional[model.HttpResource] = None
        if resource_name.endswith(".metadata"):
            resource = await self.get_metadata(project_page, resource_name)
        else:
            for file in project_page.files:
                if resource_name == file.filename:
                    resource = model.HttpResource(url=file.url)
                    break

        if not resource:
            raise errors.ResourceUnavailable(resource_name)

        try:
            resp = await self._http_client.head(
                url=resource.url,
                timeout=self._connection_timeout.total_seconds(),
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise errors.SourceRepositoryUnavailable() from e
        etag = resp.headers.get("ETag")
        if etag:
            if etag == request_context.context.get("etag"):
                # If the etag served from the source repository
                # matches the one in the request raise NotModified
                raise model.NotModified()
            resource.context["etag"] = etag

        return resource

    async def get_metadata(
        self,
        project_page: model.ProjectDetail,
        resource_name: str,
    ) -> model.HttpResource:
        distribution_name = utils.remove_suffix(resource_name, ".metadata")
        for file in project_page.files:
            if distribution_name == file.filename and file.dist_info_metadata:
                return model.HttpResource(url=file.url + ".metadata")
        raise errors.ResourceUnavailable(resource_name)
