import pathlib
import sqlite3

import pytest

from acc_py_index.cache import URLCache
from acc_py_index.simple import model

from ..mock_repository import MockRepository


@pytest.fixture
def url_cache(tmp_path: pathlib.PosixPath) -> URLCache:
    db = sqlite3.connect(tmp_path / "test.db")
    return URLCache(
        MockRepository(
            project_pages=[
                model.ProjectDetail(
                    model.Meta("1.0"), "numpy", [model.File("numpy-1.0-any.whl", "url/numpy", {})],
                ),
            ],
            resources={"numpy-1.0-any.whl": "url/numpy/resource"},
        ),
        db,
    )


@pytest.mark.asyncio
async def test_get_project_page(url_cache: URLCache) -> None:
    response = await url_cache.get_project_page("numpy")
    assert response == model.ProjectDetail(
        model.Meta("1.0"), "numpy", [model.File("numpy-1.0-any.whl", "url/numpy", {})],
    )
    assert url_cache._cache["numpy/numpy-1.0-any.whl"] == "url/numpy"


@pytest.mark.asyncio
async def test_get_resource(url_cache: URLCache) -> None:
    response = await url_cache.get_resource("numpy", "numpy-1.0-any.whl")
    assert response.value == "url/numpy/resource"

    url_cache._cache["numpy/numpy-1.0-any.whl"] = "cached_url"
    response = await url_cache.get_resource("numpy", "numpy-1.0-any.whl")
    assert response.value == "cached_url"
