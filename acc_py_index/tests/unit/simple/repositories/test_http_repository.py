from unittest import mock

import aiohttp
import pytest

from acc_py_index import errors
from acc_py_index.simple import model
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
async def test_get_project_page(
    text: str,
    header: str,
    repository: HttpRepository,
) -> None:
    response_mock = mock.Mock(spec=aiohttp.ClientResponse)
    response_mock.status = 200
    response_mock.headers = {"content-type": header}
    response_mock.text = mock.AsyncMock(return_value=text)

    repository.session.get.return_value = MockedRequestContextManager(response_mock)

    context = model.RequestContext(repository)
    resp = await repository.get_project_page("project", context)
    assert resp == model.ProjectDetail(
        name="project",
        meta=model.Meta(
            api_version="1.0",
        ),
        files=(
            model.File(
                filename="test1.whl",
                url="https://example.com/simple/project/test1.whl",
                hashes={"hash": "test_hash"},
            ),
            model.File(
                filename="test2.whl",
                url="http://test2.whl",
                hashes={},
            ),
        ),
    )


@pytest.mark.asyncio
async def test_get_project_page_unsupported_serialization(
    repository: HttpRepository,
) -> None:
    response_mock = mock.Mock(spec=aiohttp.ClientResponse)
    response_mock.status = 200
    response_mock.headers = {"content-type": "multipart/form-data"}
    response_mock.text = mock.AsyncMock(return_value="abc")

    repository.session.get.return_value = MockedRequestContextManager(response_mock)
    context = model.RequestContext(repository)

    with pytest.raises(errors.UnsupportedSerialization):
        await repository.get_project_page("project", context)


@pytest.mark.asyncio
async def test_get_project_page_failed(repository: HttpRepository) -> None:
    repository.session.get.side_effect = aiohttp.ClientResponseError(
        request_info=mock.Mock(spec=aiohttp.RequestInfo),
        history=(),
        status=404,
    )

    context = model.RequestContext(repository)
    with pytest.raises(errors.PackageNotFoundError):
        await repository.get_project_page("project", context)


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
async def test_get_project_list(
    text: str,
    header: str,
    repository: HttpRepository,
) -> None:
    response_mock = mock.Mock(spec=aiohttp.ClientResponse)
    response_mock.status = 200
    response_mock.headers = {"content-type": header}
    response_mock.text = mock.AsyncMock(return_value=text)

    mocked_session = mock.MagicMock(sepc=aiohttp.ClientSession)
    mocked_session.get.return_value = MockedRequestContextManager(response_mock)

    repository.session = mocked_session

    context = model.RequestContext(repository)
    resp = await repository.get_project_list(context)
    assert resp == model.ProjectList(
        meta=model.Meta(
            api_version="1.0",
        ),
        projects=frozenset([
            model.ProjectListElement(name="p1"),
            model.ProjectListElement(name="p2"),
        ]),
    )


@pytest.mark.asyncio
async def test_get_project_list_failed(repository: HttpRepository) -> None:
    repository.session.get.side_effect = aiohttp.ClientResponseError(
        request_info=mock.Mock(spec=aiohttp.RequestInfo),
        history=(),
        status=404,
    )

    context = model.RequestContext(repository)
    with pytest.raises(errors.SourceRepositoryUnavailable):
        await repository.get_project_list(context)


@pytest.fixture
def project_detail() -> model.ProjectDetail:
    return model.ProjectDetail(
        meta=model.Meta("1.0"),
        name="numpy",
        files=(
            model.File(
                filename="numpy-1.0.whl",
                url="my_url/numpy-1.0.whl",
                hashes={},
                dist_info_metadata={"sha256": "..."},
            ),
            model.File(
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
    project_detail: model.ProjectDetail,
    source_etag: str | None,
) -> None:
    response_mock = mock.Mock(spec=aiohttp.ClientResponse)
    response_mock.headers = {"ETag": source_etag} if source_etag else {}
    mocked_session = mock.MagicMock(spec=aiohttp.ClientSession)
    mocked_session.head.return_value = MockedRequestContextManager(response_mock)

    repository.session = mocked_session
    context = model.RequestContext(repository)

    with mock.patch.object(HttpRepository, "get_project_page", return_value=project_detail):
        resp = await repository.get_resource("numpy", "numpy-2.0.whl", context)
        assert isinstance(resp, model.HttpResource)
        assert resp.url == "my_url/numpy-2.0.whl"
        assert resp.context.get("etag") == source_etag


@pytest.mark.asyncio
async def test_get_resource_unavailable(
    repository: HttpRepository,
    project_detail: model.ProjectDetail,
) -> None:
    context = model.RequestContext(repository)
    with mock.patch.object(HttpRepository, "get_project_page", return_value=project_detail):
        with pytest.raises(errors.ResourceUnavailable, match="numpy-3.0.whl"):
            await repository.get_resource("numpy", "numpy-3.0.whl", context)


@pytest.mark.asyncio
async def test_get_resource_project_unavailable(
    repository: HttpRepository,
) -> None:
    context = model.RequestContext(repository)
    with mock.patch.object(HttpRepository, "get_project_page", side_effect=errors.PackageNotFoundError("numpy")):
        with pytest.raises(errors.ResourceUnavailable, match="numpy-3.0.whl"):
            await repository.get_resource("numpy", "numpy-3.0.whl", context)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_etag", [None, "source_etag"],
)
async def test_get_resource_metadata(
    repository: HttpRepository,
    project_detail: model.ProjectDetail,
    source_etag: str | None,
) -> None:
    response_mock = mock.Mock(spec=aiohttp.ClientResponse)
    response_mock.headers = {"ETag": source_etag} if source_etag else {}
    mocked_session = mock.MagicMock(spec=aiohttp.ClientSession)
    mocked_session.head.return_value = MockedRequestContextManager(response_mock)

    repository.session = mocked_session
    context = model.RequestContext(repository)

    with mock.patch.object(HttpRepository, "get_project_page", return_value=project_detail):
        resp = await repository.get_resource("numpy", "numpy-1.0.whl.metadata", context)
        assert isinstance(resp, model.HttpResource)
        assert resp.url == "my_url/numpy-1.0.whl.metadata"
        assert resp.context.get("etag") == source_etag

        with pytest.raises(errors.ResourceUnavailable, match="numpy-2.0.whl.metadata"):
            await repository.get_resource("numpy", "numpy-2.0.whl.metadata", context)


@pytest.mark.asyncio
async def test_get_resource_metadata__unavailable(
    repository: HttpRepository,
    project_detail: model.ProjectDetail,
) -> None:
    context = model.RequestContext(repository)
    with (
        mock.patch.object(HttpRepository, "get_project_page", return_value=project_detail),
        pytest.raises(errors.ResourceUnavailable, match="numpy-2.0.whl.metadata"),
    ):
        await repository.get_resource("numpy", "numpy-2.0.whl.metadata", context)
