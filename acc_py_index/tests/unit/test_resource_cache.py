import contextlib
from datetime import datetime
import pathlib
import sqlite3
import typing
from unittest import mock

import pytest

from acc_py_index import cache
from acc_py_index.simple import model

from ..fake_repository import FakeRepository


@pytest.fixture
def repository(tmp_path: pathlib.Path) -> typing.Generator[cache.ResourceCache, None, None]:
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
    with contextlib.closing(sqlite3.connect(tmp_path / "tmp.db")) as database:
        yield cache.ResourceCache(
            source=source,
            cache_path=tmp_path,
            session=mock.MagicMock(),
            database=database,
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


def test_resource_cache_init(tmp_path: pathlib.Path) -> None:
    real_repo = tmp_path / "dir" / "cache_repo"
    real_repo.mkdir(parents=True)

    symlink = tmp_path / "link"
    symlink.symlink_to(real_repo)

    repo = cache.ResourceCache(
        source=mock.AsyncMock(),
        cache_path=symlink,
        session=mock.MagicMock(),
        database=mock.Mock(),
    )
    assert str(symlink) != str(real_repo)
    assert str(repo._cache_path) == str(real_repo)


def get_last_access_for(repository: cache.ResourceCache, key: str) -> typing.Optional[str]:
    query = f"SELECT last_access FROM {repository._table_name} WHERE key = :key"
    res: tuple[str] = repository._database.execute(
        query, {"key": key},
    ).fetchone()
    if res:
        return res[0]
    else:
        return None


def test_update_last_access_for(repository: cache.ResourceCache) -> None:
    assert get_last_access_for(repository, "my_element") is None

    with mock.patch(
        "datetime.datetime",
        mock.Mock(
            now=mock.Mock(return_value=datetime.fromisoformat("2006-07-09")),
            fromisoformat=datetime.fromisoformat,
            spec=datetime,
        ),
    ):
        repository._update_last_access_for("my_element")

    assert get_last_access_for(repository, "my_element") == "2006-07-09 00:00:00"

    with mock.patch(
        "datetime.datetime",
        mock.Mock(
            now=mock.Mock(return_value=datetime.fromisoformat("2047-07-09")),
            fromisoformat=datetime.fromisoformat,
            spec=datetime,
        ),
    ):
        repository._update_last_access_for("my_element")

    assert get_last_access_for(repository, "my_element") == "2047-07-09 00:00:00"


@pytest.mark.asyncio
async def test_update_last_access_for__cache_hit_called(repository: cache.ResourceCache) -> None:
    cached_file = (repository._cache_path / "my_resource")
    cached_file.touch()

    update_last_access_for_mock = mock.Mock()
    with mock.patch.object(
        target=cache.ResourceCache,
        attribute="_update_last_access_for",
        new=update_last_access_for_mock,
    ):
        await repository.get_resource(
            project_name="not_used",
            resource_name="my_resource",
        )

    update_last_access_for_mock.assert_called_once_with("my_resource")


@pytest.mark.asyncio
async def test_update_last_access_for__cache_miss_local_not_called(repository: cache.ResourceCache) -> None:
    update_last_access_for_mock = mock.Mock()
    with mock.patch.object(
        target=cache.ResourceCache,
        attribute="_update_last_access_for",
        new=update_last_access_for_mock,
    ):
        await repository.get_resource(
            project_name="numpy",
            resource_name="numpy-1.0.tar.gz",
        )
    update_last_access_for_mock.assert_not_called()


@pytest.mark.asyncio
async def test_update_last_access_for__cache_miss_remote_called(repository: cache.ResourceCache) -> None:
    update_last_access_for_mock = mock.Mock()
    with mock.patch(
        "acc_py_index.utils.download_file",
        mock.AsyncMock(
            side_effect=lambda **kwargs: kwargs["dest_file"].touch(),
        ),
    ), mock.patch.object(
        target=cache.ResourceCache,
        attribute="_update_last_access_for",
        new=update_last_access_for_mock,
    ):
        await repository.get_resource(
            project_name="not_used",
            resource_name="numpy-1.0-any.whl",
        )
    update_last_access_for_mock.assert_called_once_with("numpy-1.0-any.whl")
