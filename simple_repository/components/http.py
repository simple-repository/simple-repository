# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from dataclasses import replace
from urllib.parse import urljoin

import aiohttp

from .. import errors, model, parser, utils
from .core import SimpleRepository


class HttpRepository(SimpleRepository):
    """Proxy of a remote simple repository"""

    def __init__(self, url: str, session: aiohttp.ClientSession):
        self.source_url = url
        self.session = session
        self.downstream_content_types = ", ".join([
            "application/vnd.pypi.simple.v1+json",
            "application/vnd.pypi.simple.v1+html;q=0.2",
            "text/html;q=0.01",
        ])

    async def _fetch_simple_page(
        self,
        page_url: str,
    ) -> tuple[str, str]:
        """Retrieves a simple page from the given url.
        Returns the body and the content type received.
        """
        headers = {"Accept": self.downstream_content_types}
        async with self.session.get(page_url, headers=headers) as response:
            response.raise_for_status()
            body: str = await response.text()
            content_type = response.headers.get("content-type", "")
        return body, content_type

    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectDetail:
        page_url = urljoin(self.source_url, f"{project_name}/")
        try:
            body, content_type = await self._fetch_simple_page(page_url)
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                raise errors.PackageNotFoundError(
                    package_name=project_name,
                ) from e
            raise e

        if (
            "application/vnd.pypi.simple.v1+html" in content_type or
            "text/html" in content_type or not content_type
        ):
            project_page = parser.parse_html_project_page(body, project_name)
        elif "application/vnd.pypi.simple.v1+json" in content_type:
            project_page = parser.parse_json_project_page(body)
        else:
            raise errors.UnsupportedSerialization(content_type)

        # Make the URLs in the project page absolute, such that they can be
        # resolved upstream without knowing the original source URLs.
        files = tuple(
            replace(file, url=utils.url_absolutizer(file.url, page_url))
            for file in project_page.files
        )
        project_page = replace(project_page, files=files)
        return project_page

    async def get_project_list(
        self,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectList:
        try:
            body, content_type = await self._fetch_simple_page(self.source_url)
        except aiohttp.ClientResponseError as e:
            raise errors.SourceRepositoryUnavailable() from e

        if (
            "application/vnd.pypi.simple.v1+html" in content_type or
            "text/html" in content_type or not content_type
        ):
            return parser.parse_html_project_list(body)
        elif "application/vnd.pypi.simple.v1+json" in content_type:
            return parser.parse_json_project_list(body)

        raise errors.UnsupportedSerialization(content_type)

    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.Resource:
        try:
            project_page = await self.get_project_page(
                project_name,
                request_context=request_context,
            )
        except errors.PackageNotFoundError:
            raise errors.ResourceUnavailable(resource_name)

        resource: model.HttpResource | None = None
        if resource_name.endswith(".metadata"):
            resource = await self.get_metadata(project_page, resource_name)
        else:
            for file in project_page.files:
                if resource_name == file.filename:
                    resource = model.HttpResource(url=file.url)
                    break

        if not resource:
            raise errors.ResourceUnavailable(resource_name)

        async with self.session.head(resource.url) as resp:
            if etag := resp.headers.get("ETag"):
                resource.context["etag"] = etag

        return resource

    async def get_metadata(
        self,
        project_page: model.ProjectDetail,
        resource_name: str,
    ) -> model.HttpResource:
        distribution_name = resource_name.removesuffix(".metadata")
        for file in project_page.files:
            if distribution_name == file.filename and file.dist_info_metadata:
                return model.HttpResource(url=file.url + ".metadata")
        raise errors.ResourceUnavailable(resource_name)
