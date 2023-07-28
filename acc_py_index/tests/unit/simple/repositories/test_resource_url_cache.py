import pathlib
import typing

import aiosqlite
import pytest
import pytest_asyncio

from acc_py_index.simple import model
from acc_py_index.simple.repositories.resource_url_cache import ResourceURLCacheRepository

from .fake_repository import FakeRepository


@pytest_asyncio.fixture  # type: ignore
# Untyped decorator
async def url_cache(
    tmp_path: pathlib.PosixPath,
) -> typing.AsyncGenerator[ResourceURLCacheRepository, None]:
    async with aiosqlite.connect(tmp_path / "test.db") as db:
        yield ResourceURLCacheRepository(
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        model.Meta("1.0"), "numpy", (model.File("numpy-1.0-any.whl", "url/numpy", {}),),
                    ),
                ],
                resources={
                    "numpy-1.0-any.whl": model.HttpResource("url/numpy/resource"),
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
    assert await url_cache._cache.get("numpy/numpy-1.0-any.whl") == "url/numpy"


@pytest.mark.asyncio
async def test_get_resource(url_cache: ResourceURLCacheRepository) -> None:
    response = await url_cache.get_resource("numpy", "numpy-1.0-any.whl")
    assert isinstance(response, model.HttpResource)
    assert response.url == "url/numpy/resource"

    await url_cache._cache.set("numpy/numpy-1.0-any.whl", "cached_url")
    response = await url_cache.get_resource("numpy", "numpy-1.0-any.whl")
    assert isinstance(response, model.HttpResource)
    assert response.url == "cached_url"
