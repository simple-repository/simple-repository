from typing import Protocol

import aiohttp
import packaging.utils

from . import parser
from .. import errors
from .model import ProjectDetail, ProjectList


class SimpleRepository(Protocol):
    def __init__(self) -> None:
        ...

    async def get_project_page(self, project_name: str) -> ProjectDetail:
        ...

    async def get_project_list(self) -> ProjectList:
        ...


class HttpSimpleRepository(SimpleRepository):
    """Proxys a remote simple repository"""

    CONTENT_TYPES = ", ".join([
        "application/vnd.pypi.simple.v1+json",
        "application/vnd.pypi.simple.v1+html;q=0.2",
        "text/html;q=0.01",
    ])

    def __init__(self, url: str, session: aiohttp.ClientSession):
        self.source_url = url
        self.session = session

    async def get_project_page(self, project_name: str) -> ProjectDetail:
        if project_name != packaging.utils.canonicalize_name(project_name):
            raise errors.NotNormalizedProjectName()

        headers = {"Accept": self.CONTENT_TYPES}

        page_url = self.source_url + f"{project_name}/"
        async with self.session.get(page_url, headers=headers) as response:
            if 400 <= response.status <= 499:
                raise errors.PackageNotFoundError(
                    package_name=project_name,
                )

            body: str = await response.text()
            if "application/vnd.pypi.simple.v1+json" in response.headers.get("content-type", ""):
                project_page: ProjectDetail = parser.parse_json_project_page(page_url, body)
            else:
                project_page = parser.parse_html_project_page(page_url, body, project_name)

            return project_page

    async def get_project_list(self) -> ProjectList:
        headers = {"Accept": self.CONTENT_TYPES}

        async with self.session.get(self.source_url, headers=headers) as response:
            if 400 <= response.status <= 499:
                raise errors.SourceRepositoryUnavailable()

            body = await response.text()

            if "application/vnd.pypi.simple.v1+json" in response.headers.get("content-type", ""):
                project_list: ProjectList = parser.parse_json_project_list(body)
            else:
                project_list = parser.parse_html_project_list(body)

            return project_list
