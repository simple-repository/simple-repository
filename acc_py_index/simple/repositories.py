from typing import Protocol
from urllib.parse import urljoin

import aiohttp
import packaging.utils

from . import parser
from .. import errors, utils
from .model import ProjectDetail, ProjectList


class SimpleRepository(Protocol):
    async def get_project_page(self, project_name: str) -> ProjectDetail:
        ...

    async def get_project_list(self) -> ProjectList:
        ...


class HttpSimpleRepository(SimpleRepository):
    """Proxys a remote simple repository"""

    def __init__(self, url: str, session: aiohttp.ClientSession):
        self.source_url = url
        self.session = session
        self.downstream_content_types = ", ".join([
            "application/vnd.pypi.simple.v1+json",
            "application/vnd.pypi.simple.v1+html;q=0.2",
            "text/html;q=0.01",
        ])

    async def get_project_page(self, project_name: str) -> ProjectDetail:
        if project_name != packaging.utils.canonicalize_name(project_name):
            raise errors.NotNormalizedProjectName()

        headers = {"Accept": self.downstream_content_types}

        page_url = urljoin(self.source_url, f"{project_name}/")
        async with self.session.get(page_url, headers=headers) as response:
            if response.status == 404:
                raise errors.PackageNotFoundError(
                    package_name=project_name,
                )
            response.raise_for_status()

            body: str = await response.text()
            content_type = response.headers.get("content-type", "")

        if (
            "application/vnd.pypi.simple.v1+html" in content_type or
            "text/html" in content_type or not content_type
        ):
            project_page = parser.parse_html_project_page(body, project_name)
        elif "application/vnd.pypi.simple.v1+json" in content_type:
            project_page = parser.parse_json_project_page(body)
        else:
            raise errors.UnsupportedSerialization()

        for file in project_page.files:
            # Make the URLs in the project page absolute, such that they can be
            # resolved upstream without knowing the original source URLs.
            file.url = utils.url_absolutizer(file.url, page_url)
        return project_page

    async def get_project_list(self) -> ProjectList:
        headers = {"Accept": self.downstream_content_types}

        async with self.session.get(self.source_url, headers=headers) as response:
            if response.status == 404:
                raise errors.SourceRepositoryUnavailable()
            response.raise_for_status()

            body = await response.text()
            content_type = response.headers.get("content-type", "")

        if (
            "application/vnd.pypi.simple.v1+html" in content_type or
            "text/html" in content_type or not content_type
        ):
            return parser.parse_html_project_list(body)
        elif "application/vnd.pypi.simple.v1+json" in content_type:
            return parser.parse_json_project_list(body)

        raise errors.UnsupportedSerialization()


class RepositoryContainer(SimpleRepository):
    """A base class for components that enhance the functionality of a source
    `SimpleRepository`. If not overridden, the methods provided by this class
    will delegate to the corresponding methods of the source repository.
    """
    def __init__(self, source: SimpleRepository) -> None:
        self.source = source

    async def get_project_page(self, project_name: str) -> ProjectDetail:
        return await self.source.get_project_page(project_name)

    async def get_project_list(self) -> ProjectList:
        return await self.source.get_project_list()
