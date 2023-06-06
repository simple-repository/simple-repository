import pathlib
from unittest import mock

import pytest

from acc_py_index import cache
from acc_py_index.simple import model

from ..fake_repository import FakeRepository


@pytest.fixture
def repository(tmp_path: pathlib.Path) -> cache.ResourceCache:
    source = FakeRepository(
        resources={
            "numpy-1.0-any.whl": model.Resource(
                "numpy_url/numpy-1.0-any.whl", model.ResourceType.REMOTE_RESOURCE,
            ),
            "numpy-1.0.tar.gz": model.Resource(
                "numpy_path", model.ResourceType.LOCAL_RESOURCE,
            ),
        },
    )
    return cache.ResourceCache(
        source=source,
        cache_path=tmp_path,
        session=mock.MagicMock,
    )


@pytest.mark.asyncio
async def test_get_resource__cache_hit(repository: cache.ResourceCache) -> None:
    cached_file = (repository._cache_path / "my_resource")
    cached_file.touch()

    resource = await repository.get_resource(
        project_name="not_used",
        resource_name="my_resource",
    )

    assert resource.value == str(cached_file)
    assert resource.type == model.ResourceType.LOCAL_RESOURCE


@pytest.mark.asyncio
async def test_get_resource__cache_miss_remote(repository: cache.ResourceCache) -> None:
    with mock.patch(
        "acc_py_index.utils.download_file",
        mock.AsyncMock(
            side_effect=lambda **kwargs: kwargs["dest_file"].touch(),
        ),
    ):
        response = await repository.get_resource(
            project_name="not_used",
            resource_name="numpy-1.0-any.whl",
        )

    assert response.type == model.ResourceType.LOCAL_RESOURCE
    assert response.value == str(repository._cache_path / "numpy-1.0-any.whl")


@pytest.mark.asyncio
async def test_get_resource__cache_miss_local(repository: cache.ResourceCache) -> None:
    resource = await repository.get_resource(
        project_name="numpy",
        resource_name="numpy-1.0.tar.gz",
    )

    assert resource.type == model.ResourceType.LOCAL_RESOURCE
    assert resource.value == "numpy_path"


@pytest.mark.asyncio
async def test_get_resource__path_traversal(repository: cache.ResourceCache) -> None:
    with pytest.raises(
        ValueError,
        match="is not contained in",
    ):
        await repository.get_resource(
            project_name="not_used",
            resource_name="../../../etc/passwords",
        )
