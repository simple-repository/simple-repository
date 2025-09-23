# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import typing
from unittest import mock

import httpx
import pytest

from ... import errors, model
from ...components.http import HttpRepository, _url_path_append
from .mock_compat import AsyncMock

if typing.TYPE_CHECKING:
    import pytest_httpx


@pytest.mark.parametrize(
    ("base_url", "append_with", "target"),
    [
        [
            "https://example.com/simple",
            "my_project",
            "https://example.com/simple/my_project",
        ],
        [
            "https://example.com/what/",
            "my_project",
            "https://example.com/what/my_project",
        ],
        [
            "http://example.com/what/",
            "my_project",
            "http://example.com/what/my_project",
        ],
        [
            "http://example.com/what/",
            "my_project/",
            "http://example.com/what/my_project/",
        ],
        [
            "http://example.com/what/",
            "/my_project/",
            "http://example.com/what/my_project/",
        ],
        [
            "http://example.com/what/",
            "/my_project",
            "http://example.com/what/my_project",
        ],
        [
            "https://example.com/simple?foo=bar",
            "my_project",
            "https://example.com/simple/my_project?foo=bar",
        ],
        [
            "https://example.com/simple?foo=bar",
            "my_project/",
            "https://example.com/simple/my_project/?foo=bar",
        ],
    ],
)
def test___url_path_append(base_url: str, append_with: str, target: str):
    assert _url_path_append(base_url, append_with) == target


@pytest.mark.parametrize(
    ("base_url", "target"),
    [
        ["https://example.com/simple", "https://example.com/simple/my_project/"],
        ["https://example.com/what/", "https://example.com/what/my_project/"],
        ["http://example.com/what/", "http://example.com/what/my_project/"],
        [
            "https://example.com/simple?foo=bar",
            "https://example.com/simple/my_project/?foo=bar",
        ],
    ],
)
@pytest.mark.asyncio
async def test_http_repository__no_trailing_slash(base_url: str, target: str) -> None:
    repo = HttpRepository(url=base_url)
    with mock.patch.object(repo, "_fetch_simple_page") as _fetch_simple_page:
        _fetch_simple_page.side_effect = ValueError("some unhandled exception")

        with pytest.raises(ValueError, match="some unhandled exception"):
            await repo.get_project_page("my_project")

        _fetch_simple_page.assert_called_once_with(target)


@pytest.mark.parametrize(
    ("text", "header"),
    [
        (
            """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <a href="test1.whl#hash=test_hash">test1.whl</a>
                <a href="http://test2.whl">test2.whl</a>
            </body>
        </html>
        """,
            "application/vnd.pypi.simple.v1+html",
        ),
        (
            """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <a href="test1.whl#hash=test_hash">test1.whl</a>
                <a href="http://test2.whl">test2.whl</a>
            </body>
        </html>
        """,
            "",
        ),
        (
            """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <a href="test1.whl#hash=test_hash">test1.whl</a>
                <a href="http://test2.whl">test2.whl</a>
            </body>
        </html>
        """,
            "text/html",
        ),
        (
            """
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
        """,
            "application/vnd.pypi.simple.v1+json",
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_project_page(
    text: str,
    header: str,
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
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
async def test_get_project_page_unsupported_serialization(
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_response(
        content="abc",
        headers={"content-type": "multipart/form-data"},
    )

    with pytest.raises(errors.UnsupportedSerialization):
        await repository.get_project_page("project")


@pytest.mark.asyncio
async def test_get_project_page__package_not_found(
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_response(status_code=404)

    with pytest.raises(errors.PackageNotFoundError):
        await repository.get_project_page("project")


@pytest.mark.parametrize(
    "status_code",
    [400, 401, 403, 500, 501],
)
@pytest.mark.asyncio
async def test_get_project_page__bad_status_code(
    httpx_mock: pytest_httpx.HTTPXMock,
    status_code: int,
) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_response(status_code=status_code)

    with pytest.raises(errors.SourceRepositoryUnavailable) as exc:
        await repository.get_project_page("project")
    exc.value.__context__ == httpx.HTTPStatusError


@pytest.mark.asyncio
async def test_get_project_page__http_error(httpx_mock: pytest_httpx.HTTPXMock) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_exception(httpx.HTTPError("Error"))

    with pytest.raises(errors.SourceRepositoryUnavailable) as exc:
        await repository.get_project_page("project")
    exc.value.__context__ == httpx.HTTPError


@pytest.mark.parametrize(
    ("text", "header"),
    [
        (
            """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <a href="/p1/">p1</a>
                <a href="/p2/">p2</a>
            </body>
        </html>
        """,
            "text/html",
        ),
        (
            """
        {
            "meta": {
                "api-version": "1.0"
            },
            "projects": [
                {"name": "p1"},
                {"name": "p2"}
            ]
        }
        """,
            "application/vnd.pypi.simple.v1+json",
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_project_list(
    text: str,
    header: str,
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_response(content=text, headers={"content-type": header})

    resp = await repository.get_project_list()
    assert resp == model.ProjectList(
        meta=model.Meta(
            api_version="1.0",
        ),
        projects=frozenset(
            [
                model.ProjectListElement(name="p1"),
                model.ProjectListElement(name="p2"),
            ],
        ),
    )


@pytest.mark.parametrize(
    "status_code",
    [400, 401, 403, 404, 500, 501],
)
@pytest.mark.asyncio
async def test_get_project_list__bad_status_code(
    httpx_mock: pytest_httpx.HTTPXMock,
    status_code: int,
) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_response(status_code=status_code)

    with pytest.raises(errors.SourceRepositoryUnavailable) as exc:
        await repository.get_project_list()
    exc.value.__context__ == httpx.HTTPStatusError


@pytest.mark.asyncio
async def test_get_project_list__http_error(httpx_mock: pytest_httpx.HTTPXMock) -> None:
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
    "source_etag",
    [None, "source_etag"],
)
async def test_get_resource(
    project_detail: model.ProjectDetail,
    source_etag: typing.Optional[str],
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_response(headers={"ETag": source_etag} if source_etag else {})

    with mock.patch.object(
        repository,
        "get_project_page",
        AsyncMock(return_value=project_detail),
    ):
        resp = await repository.get_resource("numpy", "numpy-2.0.whl")
        assert isinstance(resp, model.HttpResource)
        assert resp.url == "http://my_url/numpy-2.0.whl"
        assert resp.context.get("etag") == source_etag


@pytest.mark.asyncio
async def test_get_resource__not_modified(
    project_detail: model.ProjectDetail,
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    etag = "my_etag"
    httpx_mock.add_response(headers={"ETag": etag})

    with mock.patch.object(
        repository,
        "get_project_page",
        AsyncMock(return_value=project_detail),
    ):
        with pytest.raises(model.NotModified):
            await repository.get_resource(
                project_name="numpy",
                resource_name="numpy-2.0.whl",
                request_context=model.RequestContext({"etag": etag}),
            )


@pytest.mark.asyncio
async def test_get_resource_unavailable(
    project_detail: model.ProjectDetail,
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    with mock.patch.object(
        repository,
        "get_project_page",
        AsyncMock(return_value=project_detail),
    ):
        with pytest.raises(errors.ResourceUnavailable, match="numpy-3.0.whl"):
            await repository.get_resource("numpy", "numpy-3.0.whl")


@pytest.mark.asyncio
async def test_get_resource_project_unavailable(
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    with mock.patch.object(
        repository,
        "get_project_page",
        side_effect=errors.PackageNotFoundError("numpy"),
    ):
        with pytest.raises(errors.PackageNotFoundError, match="numpy"):
            await repository.get_resource("numpy", "numpy-3.0.whl")


@pytest.mark.asyncio
async def test_get_resource__http_error(
    httpx_mock: pytest_httpx.HTTPXMock,
    project_detail: model.ProjectDetail,
) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_exception(httpx.HTTPError("error"), method="HEAD")

    with mock.patch.object(
        repository,
        "get_project_page",
        AsyncMock(return_value=project_detail),
    ):
        with pytest.raises(errors.SourceRepositoryUnavailable) as exc:
            await repository.get_resource("numpy", "numpy-2.0.whl")
    exc.value.__context__ == httpx.HTTPError


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_etag",
    [None, "source_etag"],
)
async def test_get_resource_metadata(
    project_detail: model.ProjectDetail,
    source_etag: typing.Optional[str],
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
    repository = HttpRepository(url="https://example.com/simple/")
    httpx_mock.add_response(headers={"ETag": source_etag} if source_etag else {})

    with mock.patch.object(
        repository,
        "get_project_page",
        AsyncMock(return_value=project_detail),
    ):
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
    with mock.patch.object(
        repository,
        "get_project_page",
        AsyncMock(return_value=project_detail),
    ):
        with pytest.raises(errors.ResourceUnavailable, match="numpy-2.0.whl.metadata"):
            await repository.get_resource("numpy", "numpy-2.0.whl.metadata")


@pytest.mark.asyncio
async def test_get_resource__authentication_preserved_in_head_request(
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
    # Verify that if we use auth in the http client, it will be honoured in
    # the right places such that you can be sure to be authenticated for
    # subsequent get_resource requests.
    auth = httpx.BasicAuth("test_user", "test_password")
    http_client = httpx.AsyncClient(auth=auth)
    repository = HttpRepository(
        url="https://example.com/simple/",
        http_client=http_client,
    )

    project_page_html = """
        <html><body>
            <a href="http://files.example.com/numpy-2.0.whl">numpy-2.0.whl</a><br/>
        </body></html>
    """

    def check_auth_header(request: httpx.Request) -> httpx.Response:
        assert "Authorization" in request.headers
        assert (
            request.headers["Authorization"] == "Basic dGVzdF91c2VyOnRlc3RfcGFzc3dvcmQ="
        )  # base64 of "test_user:test_password"
        if request.method == "GET":
            return httpx.Response(
                200,
                content=project_page_html,
                headers={"content-type": "text/html"},
            )
        elif request.method == "HEAD":
            return httpx.Response(200, headers={"ETag": "test_etag"})
        return httpx.Response(404)

    # Register callback for both the main repository domain and the file domain
    httpx_mock.add_callback(check_auth_header, url="https://example.com/simple/numpy/")
    httpx_mock.add_callback(
        check_auth_header,
        url="http://files.example.com/numpy-2.0.whl",
    )

    resp = await repository.get_resource("numpy", "numpy-2.0.whl")
    assert isinstance(resp, model.HttpResource)
    assert resp.url == "http://files.example.com/numpy-2.0.whl"
    assert resp.context.get("etag") == "test_etag"


@pytest.mark.asyncio
async def test_get_resource__redirect_followed(
    project_detail: model.ProjectDetail,
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
    repository = HttpRepository(url="https://example.com/simple/")

    # Mock the HEAD request returning a redirect
    httpx_mock.add_response(
        url="http://my_url/numpy-2.0.whl",
        method="HEAD",
        status_code=302,
        headers={"Location": "https://pypi.org/files/numpy-2.0.whl"},
    )

    # Mock the final HEAD response after redirect
    httpx_mock.add_response(
        url="https://pypi.org/files/numpy-2.0.whl",
        method="HEAD",
        status_code=200,
        headers={"ETag": "test_etag"},
    )

    with mock.patch.object(
        repository,
        "get_project_page",
        AsyncMock(return_value=project_detail),
    ):
        resp = await repository.get_resource("numpy", "numpy-2.0.whl")
        assert isinstance(resp, model.HttpResource)
        # Note that the URL in the resource remains un-redirected.
        assert resp.url == "http://my_url/numpy-2.0.whl"
        assert resp.context.get("etag") == "test_etag"
