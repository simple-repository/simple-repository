from unittest import mock

import aiohttp
import pytest

from acc_py_index import errors
from acc_py_index.simple.model import (
    File,
    HttpResource,
    Meta,
    ProjectDetail,
    ProjectList,
    ProjectListElement,
)
from acc_py_index.simple.repositories.http import HttpRepository
from acc_py_index.tests.aiohttp_mock import MockedRequestContextManager


@pytest.fixture
def repository() -> HttpRepository:
    repo = HttpRepository(
        url="https://example.com/simple/",
        session=mock.MagicMock(),
    )
    return repo


@pytest.mark.parametrize(
    ("text", "header"), [
        (
            '''
        <html>
            <head><title>Test Page</title></head>
            <body>
                <a href="test1.whl#hash=test_hash">test1.whl</a>
                <a href="http://test2.whl">test2.whl</a>
            </body>
        </html>
        ''', "application/vnd.pypi.simple.v1+html",
        ),
        (
            '''
        <html>
            <head><title>Test Page</title></head>
            <body>
                <a href="test1.whl#hash=test_hash">test1.whl</a>
                <a href="http://test2.whl">test2.whl</a>
            </body>
        </html>
        ''', "",
        ),
        (
            '''
        <html>
            <head><title>Test Page</title></head>
            <body>
                <a href="test1.whl#hash=test_hash">test1.whl</a>
                <a href="http://test2.whl">test2.whl</a>
            </body>
        </html>
        ''', "text/html",
        ),
        (
            '''
        {
            "meta": {
                "api-version": "1.0"
            },
            "name": "project",
            "files": [
                {
                    "filename": "test1.whl",
                    "url": "test1.whl",
                    "hashes": {"hash": "test_hash"}
                },
                {
                    "filename": "test2.whl",
                    "url": "http://test2.whl",
                    "hashes": {}
                }
            ]
        }
        ''', "application/vnd.pypi.simple.v1+json",
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_project_page(text: str, header: str, repository: HttpRepository) -> None:
    response_mock = mock.Mock(spec=aiohttp.ClientResponse)
    response_mock.status = 200
    response_mock.headers = {"content-type": header}
    response_mock.text = mock.AsyncMock(return_value=text)

    repository.session.get.return_value = MockedRequestContextManager(response_mock)

    resp = await repository.get_project_page("project")
    assert resp == ProjectDetail(
        name="project",
        meta=Meta(
            api_version="1.0",
        ),
        files=(
            File(
                filename="test1.whl",
                url="https://example.com/simple/project/test1.whl",
                hashes={"hash": "test_hash"},
            ),
            File(
                filename="test2.whl",
                url="http://test2.whl",
                hashes={},
            ),
        ),
    )


@pytest.mark.asyncio
async def test_get_project_page_unsupported_serialization(repository: HttpRepository) -> None:
    response_mock = mock.Mock(spec=aiohttp.ClientResponse)
    response_mock.status = 200
    response_mock.headers = {"content-type": "multipart/form-data"}
    response_mock.text = mock.AsyncMock(return_value="abc")

    repository.session.get.return_value = MockedRequestContextManager(response_mock)

    with pytest.raises(errors.UnsupportedSerialization):
        await repository.get_project_page("project")


@pytest.mark.asyncio
async def test_get_project_page_failed(repository: HttpRepository) -> None:
    repository.session.get.side_effect = aiohttp.ClientResponseError(
        request_info=mock.Mock(spec=aiohttp.RequestInfo),
        history=(),
        status=404,
    )

    with pytest.raises(errors.PackageNotFoundError):
        await repository.get_project_page("project")


@pytest.mark.parametrize(
    ("text", "header"), [
        (
            '''
        <html>
            <head><title>Test Page</title></head>
            <body>
                <a href="/p1/">p1</a>
                <a href="/p2/">p2</a>
            </body>
        </html>
        ''', "text/html",
        ),
        (
            '''
        {
            "meta": {
                "api-version": "1.0"
            },
            "projects": [
                {"name": "p1"},
                {"name": "p2"}
            ]
        }
        ''', "application/vnd.pypi.simple.v1+json",
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_project_list(text: str, header: str, repository: HttpRepository) -> None:
    response_mock = mock.Mock(spec=aiohttp.ClientResponse)
    response_mock.status = 200
    response_mock.headers = {"content-type": header}
    response_mock.text = mock.AsyncMock(return_value=text)

    mocked_session = mock.MagicMock(sepc=aiohttp.ClientSession)
    mocked_session.get.return_value = MockedRequestContextManager(response_mock)

    repository.session = mocked_session

    resp = await repository.get_project_list()
    assert resp == ProjectList(
        meta=Meta(
            api_version="1.0",
        ),
        projects=frozenset([
            ProjectListElement(name="p1"),
            ProjectListElement(name="p2"),
        ]),
    )


@pytest.mark.asyncio
async def test_get_project_list_failed(repository: HttpRepository) -> None:
    repository.session.get.side_effect = aiohttp.ClientResponseError(
        request_info=mock.Mock(spec=aiohttp.RequestInfo),
        history=(),
        status=404,
    )

    with pytest.raises(errors.SourceRepositoryUnavailable):
        await repository.get_project_list()


@pytest.mark.asyncio
async def test_not_normalized_package(repository: HttpRepository) -> None:
    with pytest.raises(errors.NotNormalizedProjectName):
        await repository.get_project_page("non_normalized")


@pytest.fixture
def project_detail() -> ProjectDetail:
    return ProjectDetail(
        meta=Meta("1.0"),
        name="numpy",
        files=(
            File(
                filename="numpy-1.0.whl",
                url="my_url/numpy-1.0.whl",
                hashes={},
                dist_info_metadata={"sha256": "..."},
            ),
            File(
                filename="numpy-2.0.whl",
                url="my_url/numpy-2.0.whl",
                hashes={},
            ),
        ),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_etag", [None, "source_etag"],
)
async def test_get_resource(
    repository: HttpRepository,
    project_detail: ProjectDetail,
    source_etag: str | None,
) -> None:
    response_mock = mock.Mock(spec=aiohttp.ClientResponse)
    response_mock.headers = {"ETag": source_etag} if source_etag else {}
    mocked_session = mock.MagicMock(spec=aiohttp.ClientSession)
    mocked_session.head.return_value = MockedRequestContextManager(response_mock)

    repository.session = mocked_session

    with mock.patch.object(HttpRepository, "get_project_page", return_value=project_detail):
        resp = await repository.get_resource("numpy", "numpy-2.0.whl")
        assert isinstance(resp, HttpResource)
        assert resp.url == "my_url/numpy-2.0.whl"
        assert resp.context.get("etag") == source_etag


@pytest.mark.asyncio
async def test_get_resource_unavailable(repository: HttpRepository, project_detail: ProjectDetail) -> None:
    with mock.patch.object(HttpRepository, "get_project_page", return_value=project_detail):
        with pytest.raises(errors.ResourceUnavailable, match="numpy-3.0.whl"):
            await repository.get_resource("numpy", "numpy-3.0.whl")


@pytest.mark.asyncio
async def test_get_resource_project_unavailable(repository: HttpRepository) -> None:
    with mock.patch.object(HttpRepository, "get_project_page", side_effect=errors.PackageNotFoundError("numpy")):
        with pytest.raises(errors.ResourceUnavailable, match="numpy-3.0.whl"):
            await repository.get_resource("numpy", "numpy-3.0.whl")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_etag", [None, "source_etag"],
)
async def test_get_resource_metadata(
    repository: HttpRepository,
    project_detail: ProjectDetail,
    source_etag: str | None,
) -> None:
    response_mock = mock.Mock(spec=aiohttp.ClientResponse)
    response_mock.headers = {"ETag": source_etag} if source_etag else {}
    mocked_session = mock.MagicMock(spec=aiohttp.ClientSession)
    mocked_session.head.return_value = MockedRequestContextManager(response_mock)

    repository.session = mocked_session

    with mock.patch.object(HttpRepository, "get_project_page", return_value=project_detail):
        resp = await repository.get_resource("numpy", "numpy-1.0.whl.metadata")
        assert isinstance(resp, HttpResource)
        assert resp.url == "my_url/numpy-1.0.whl.metadata"
        assert resp.context.get("etag") == source_etag

        with pytest.raises(errors.ResourceUnavailable, match="numpy-2.0.whl.metadata"):
            await repository.get_resource("numpy", "numpy-2.0.whl.metadata")


@pytest.mark.asyncio
async def test_get_resource_metadata__unavailable(repository: HttpRepository, project_detail: ProjectDetail) -> None:
    with (
        mock.patch.object(HttpRepository, "get_project_page", return_value=project_detail),
        pytest.raises(errors.ResourceUnavailable, match="numpy-2.0.whl.metadata"),
    ):
        await repository.get_resource("numpy", "numpy-2.0.whl.metadata")
