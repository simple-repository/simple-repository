from unittest import mock

import pytest

from acc_py_index import errors
from acc_py_index.simple.model import File, Meta, ProjectDetail, ProjectList, ProjectListElement
from acc_py_index.simple.repositories import HttpSimpleRepository
from acc_py_index.tests.aiohttp_mock import MockedRequestContextManager


@pytest.fixture
def repository() -> HttpSimpleRepository:
    repo = HttpSimpleRepository(
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
                <a href="test1.whl#hash=test_hash" data-requires-python=">4.0" data-dist-info-metadata="true" data-yanked="yanked">test1.whl</a>
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
                    "hashes": {"hash": "test_hash"},
                    "requires-python": ">4.0",
                    "yanked": "yanked",
                    "dist-info-metadata": "true"
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
async def test_get_project_page(text: str, header: str, repository: HttpSimpleRepository) -> None:
    response_mock = mock.Mock()
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
        files=[
            File(
                filename="test1.whl",
                url="https://example.com/simple/project/test1.whl",
                hashes={"hash": "test_hash"},
                requires_python=">4.0",
                dist_info_metadata="true",
                yanked="yanked",
            ),
            File(
                filename="test2.whl",
                url="http://test2.whl",
                hashes={},
            ),
        ],
    )


@pytest.mark.asyncio
async def test_get_project_page_failed(repository: HttpSimpleRepository) -> None:
    response_mock = mock.Mock()
    response_mock.status = 404

    repository.session.get.return_value = MockedRequestContextManager(response_mock)

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
async def test_get_project_list(text: str, header: str, repository: HttpSimpleRepository) -> None:
    response_mock = mock.Mock()
    response_mock.status = 200

    response_mock.headers = {"content-type": header}
    response_mock.text = mock.AsyncMock(return_value=text)

    mocked_session = mock.MagicMock()
    mocked_session.get.return_value = MockedRequestContextManager(response_mock)

    repository.session = mocked_session

    resp = await repository.get_project_list()
    assert resp == ProjectList(
        meta=Meta(
            api_version="1.0",
        ),
        projects={
            ProjectListElement(name="p1"),
            ProjectListElement(name="p2"),
        },
    )


@pytest.mark.asyncio
async def test_get_project_list_failed(repository: HttpSimpleRepository) -> None:
    response_mock = mock.Mock()
    response_mock.status = 404

    mocked_session = mock.MagicMock()
    mocked_session.get.return_value = MockedRequestContextManager(response_mock)

    repository.session = mocked_session

    with pytest.raises(errors.SourceRepositoryUnavailable):
        await repository.get_project_list()
