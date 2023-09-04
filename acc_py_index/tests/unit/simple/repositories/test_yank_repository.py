from typing import Optional, Union
from unittest import mock

import aiosqlite
import pytest

from acc_py_index.simple import model
import acc_py_index.simple.repositories.yanking as yank_repository

from .fake_repository import FakeRepository


@pytest.mark.parametrize(
    "yank_reason, yank_attribute", [
        ("reason", "reason"), ("", True),
    ],
)
def test_add_yanked_attribute(
    yank_reason: str,
    yank_attribute: Union[str, bool],
) -> None:
    project_page = model.ProjectDetail(
        name="project",
        meta=model.Meta("1.0"),
        files=(
            model.File(
              filename="project-1.0.0-any.whl",
              url="url",
              hashes={},
            ),
            model.File(
              filename="project-1.0.0.tar.gz",
              url="url",
              hashes={},
            ),
        ),
    )

    yanked_data = {"project-1.0.0-any.whl": yank_reason}
    yanked_page = yank_repository.add_yanked_attribute(
        project_page,
        yanked_data,
    )
    assert yanked_page.files[0].yanked == yank_attribute
    assert yanked_page.files[1].yanked is None


@pytest.mark.parametrize(
    "yanked_versions, yanked_value", [
        ({}, None),
        ({"project1.0.whl": "reason"}, "reason"),
        ({"project1.0.whl": ""}, True),
    ],
)
@pytest.mark.asyncio
async def test_get_project_page(
    yanked_versions: dict[str, str],
    yanked_value: Optional[Union[bool, str]],
) -> None:
    repository = yank_repository.YankRepository(
        FakeRepository(
            project_pages=[
                model.ProjectDetail(
                    model.Meta("1.0"), name="project", files=(
                        model.File("project1.0.whl", "url", {}), model.File("project1.1.whl", "url", {}),
                    ),
                ),
            ],
        ),
        mock.AsyncMock(),
    )

    with mock.patch(
        "acc_py_index.simple.repositories.yanking.get_yanked_releases",
        mock.AsyncMock(return_value=yanked_versions),
    ):
        result = await repository.get_project_page("project", model.RequestContext(repository))

    assert result.files[0].yanked == yanked_value
    assert result.files[1].yanked is None


@pytest.mark.asyncio
async def test_get_yanked_releases() -> None:
    mock_database = mock.AsyncMock(spec=aiosqlite.Connection)
    mock_database.execute.return_value.__aenter__.return_value.fetchall = mock.AsyncMock(
        return_value=[("file1", "reason1"), ("file2", "reason2")],
    )

    versions = await yank_repository.get_yanked_releases("project_name", mock_database)

    assert versions == {"file1": "reason1", "file2": "reason2"}
