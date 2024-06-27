# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from unittest import mock

import httpx
import pytest
from pytest_httpx import HTTPXMock

from ... import errors, model
from ...components.http import HttpRepository


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
async def test_get_project_page(text: str, header: str, httpx_mock: HTTPXMock) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_response(content=text, headers={"content-type": header})

    resp = await repository.get_project_page("project")
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
async def test_get_project_page_unsupported_serialization(httpx_mock: HTTPXMock) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_response(content="abc", headers={"content-type": "multipart/form-data"})

    with pytest.raises(errors.UnsupportedSerialization):
        await repository.get_project_page("project")


@pytest.mark.asyncio
async def test_get_project_page__package_not_found(httpx_mock: HTTPXMock) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_response(status_code=404)

    with pytest.raises(errors.PackageNotFoundError):
        await repository.get_project_page("project")


@pytest.mark.parametrize(
    "status_code", [400, 401, 403, 500, 501],
)
@pytest.mark.asyncio
async def test_get_project_page__bad_status_code(httpx_mock: HTTPXMock, status_code: int) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_response(status_code=status_code)

    with pytest.raises(errors.SourceRepositoryUnavailable) as exc:
        await repository.get_project_page("project")
    exc.value.__context__ == httpx.HTTPStatusError


@pytest.mark.asyncio
async def test_get_project_page__http_error(httpx_mock: HTTPXMock) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_exception(httpx.HTTPError("Error"))

    with pytest.raises(errors.SourceRepositoryUnavailable) as exc:
        await repository.get_project_page("project")
    exc.value.__context__ == httpx.HTTPError


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
async def test_get_project_list(text: str, header: str, httpx_mock: HTTPXMock) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_response(content=text, headers={"content-type": header})

    resp = await repository.get_project_list()
    assert resp == model.ProjectList(
        meta=model.Meta(
            api_version="1.0",
        ),
        projects=frozenset([
            model.ProjectListElement(name="p1"),
            model.ProjectListElement(name="p2"),
        ]),
    )


@pytest.mark.parametrize(
    "status_code", [400, 401, 403, 404, 500, 501],
)
@pytest.mark.asyncio
async def test_get_project_list__bad_status_code(httpx_mock: HTTPXMock, status_code: int) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_response(status_code=status_code)

    with pytest.raises(errors.SourceRepositoryUnavailable) as exc:
        await repository.get_project_list()
    exc.value.__context__ == httpx.HTTPStatusError


@pytest.mark.asyncio
async def test_get_project_list__http_error(httpx_mock: HTTPXMock) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_exception(httpx.HTTPError("Error"))

    with pytest.raises(errors.SourceRepositoryUnavailable) as exc:
        await repository.get_project_list()
    exc.value.__context__ == httpx.HTTPError


@pytest.fixture
def project_detail() -> model.ProjectDetail:
    return model.ProjectDetail(
        meta=model.Meta("1.0"),
        name="numpy",
        files=(
            model.File(
                filename="numpy-1.0.whl",
                url="http://my_url/numpy-1.0.whl",
                hashes={},
                dist_info_metadata={"sha256": "..."},
            ),
            model.File(
                filename="numpy-2.0.whl",
                url="http://my_url/numpy-2.0.whl",
                hashes={},
            ),
        ),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_etag", [None, "source_etag"],
)
async def test_get_resource(
    project_detail: model.ProjectDetail,
    source_etag: str | None,
    httpx_mock: HTTPXMock,
) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_response(headers={"ETag": source_etag} if source_etag else {})

    with mock.patch.object(repository, "get_project_page", return_value=project_detail):
        resp = await repository.get_resource("numpy", "numpy-2.0.whl")
        assert isinstance(resp, model.HttpResource)
        assert resp.url == "http://my_url/numpy-2.0.whl"
        assert resp.context.get("etag") == source_etag


@pytest.mark.asyncio
async def test_get_resource__not_modified(
    project_detail: model.ProjectDetail,
    httpx_mock: HTTPXMock,
) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    etag = "my_etag"
    httpx_mock.add_response(headers={"ETag": etag})

    with (
        mock.patch.object(repository, "get_project_page", return_value=project_detail),
        pytest.raises(model.NotModified),
    ):
        await repository.get_resource(
            project_name="numpy",
            resource_name="numpy-2.0.whl",
            request_context=model.RequestContext(repository, {"etag": etag}),
        )


@pytest.mark.asyncio
async def test_get_resource_unavailable(project_detail: model.ProjectDetail, httpx_mock: HTTPXMock) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    with mock.patch.object(repository, "get_project_page", return_value=project_detail):
        with pytest.raises(errors.ResourceUnavailable, match="numpy-3.0.whl"):
            await repository.get_resource("numpy", "numpy-3.0.whl")


@pytest.mark.asyncio
async def test_get_resource_project_unavailable(httpx_mock: HTTPXMock) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    with mock.patch.object(repository, "get_project_page", side_effect=errors.PackageNotFoundError("numpy")):
        with pytest.raises(errors.ResourceUnavailable, match="numpy-3.0.whl"):
            await repository.get_resource("numpy", "numpy-3.0.whl")


@pytest.mark.asyncio
async def test_get_resource__http_error(httpx_mock: HTTPXMock, project_detail: model.ProjectDetail) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_exception(httpx.HTTPError("error"), method="HEAD")

    with (
        pytest.raises(errors.SourceRepositoryUnavailable) as exc,
        mock.patch.object(repository, "get_project_page", return_value=project_detail),
    ):
        await repository.get_resource("numpy", "numpy-2.0.whl")
    exc.value.__context__ == httpx.HTTPError


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_etag", [None, "source_etag"],
)
async def test_get_resource_metadata(
    project_detail: model.ProjectDetail,
    source_etag: str | None,
    httpx_mock: HTTPXMock,
) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_response(headers={"ETag": source_etag} if source_etag else {})

    with mock.patch.object(repository, "get_project_page", return_value=project_detail):
        resp = await repository.get_resource("numpy", "numpy-1.0.whl.metadata")
        assert isinstance(resp, model.HttpResource)
        assert resp.url == "http://my_url/numpy-1.0.whl.metadata"
        assert resp.context.get("etag") == source_etag

        with pytest.raises(errors.ResourceUnavailable, match="numpy-2.0.whl.metadata"):
            await repository.get_resource("numpy", "numpy-2.0.whl.metadata")


@pytest.mark.asyncio
async def test_get_resource_metadata__unavailable(
    project_detail: model.ProjectDetail,
) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    with (
        mock.patch.object(repository, "get_project_page", return_value=project_detail),
        pytest.raises(errors.ResourceUnavailable, match="numpy-2.0.whl.metadata"),
    ):
        await repository.get_resource("numpy", "numpy-2.0.whl.metadata")
