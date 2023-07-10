import pathlib
import sqlite3

import pytest

from acc_py_index.simple import model
from acc_py_index.simple.repositories.resource_url_cache import ResourceURLCacheRepository

from .fake_repository import FakeRepository


@pytest.fixture
def url_cache(tmp_path: pathlib.PosixPath) -> ResourceURLCacheRepository:
    db = sqlite3.connect(tmp_path / "test.db")
    return ResourceURLCacheRepository(
        FakeRepository(
            project_pages=[
                model.ProjectDetail(
                    model.Meta("1.0"), "numpy", (model.File("numpy-1.0-any.whl", "url/numpy", {}),),
                ),
            ],
            resources={
                "numpy-1.0-any.whl": model.Resource(
                    "url/numpy/resource", model.ResourceType.REMOTE_RESOURCE,
                ),
            },
        ),
        db,
    )


@pytest.mark.asyncio
async def test_get_project_page(url_cache: ResourceURLCacheRepository) -> None:
    response = await url_cache.get_project_page("numpy")
    assert response == model.ProjectDetail(
        model.Meta("1.0"), "numpy", (model.File("numpy-1.0-any.whl", "url/numpy", {}),),
    )
    assert url_cache._cache["numpy/numpy-1.0-any.whl"] == "url/numpy"


@pytest.mark.asyncio
async def test_get_resource(url_cache: ResourceURLCacheRepository) -> None:
    response = await url_cache.get_resource("numpy", "numpy-1.0-any.whl")
    assert response.value == "url/numpy/resource"

    url_cache._cache["numpy/numpy-1.0-any.whl"] = "cached_url"
    response = await url_cache.get_resource("numpy", "numpy-1.0-any.whl")
    assert response.value == "cached_url"
