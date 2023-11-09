from datetime import datetime, timedelta
from unittest import mock

import pytest

from ... import model
from ...components.new_releases_remover import NewReleasesRemover
from .fake_repository import FakeRepository


def create_project_detail(*dates: datetime | None) -> model.ProjectDetail:
    files = tuple(
        model.File(
            filename=f"project-{i}.whl",
            url="url",
            hashes={},
            upload_time=date,
        ) for i, date in enumerate(dates)
    )

    return model.ProjectDetail(
        meta=model.Meta("1.0"),
        name="project",
        files=files,
    )


def test_exclude_recent_distributions__old_files() -> None:
    repository = NewReleasesRemover(
        source=FakeRepository(),
        quarantine_time=timedelta(days=10),
    )
    now = datetime(2023, 1, 1)
    project_detail = create_project_detail(datetime(1926, 1, 1), datetime(2000, 1, 4))
    new_project_detail = repository._exclude_recent_distributions(project_detail, now)
    assert new_project_detail == project_detail


def test_exclude_recent_distributions__new_files() -> None:
    repository = NewReleasesRemover(
        source=FakeRepository(),
        quarantine_time=timedelta(days=10),
    )

    now = datetime(2023, 1, 1)
    project_detail = create_project_detail(now, now - timedelta(days=1), now - timedelta(days=11))
    new_project_detail = repository._exclude_recent_distributions(project_detail, now)
    assert new_project_detail != project_detail
    assert len(new_project_detail.files) == 1
    assert new_project_detail.files[0].upload_time == now - timedelta(days=11)


@pytest.mark.asyncio
async def test_get_project_page() -> None:
    repository = NewReleasesRemover(
        source=FakeRepository(
            project_pages=[
                create_project_detail(
                    datetime.now(),
                    datetime(1926, 1, 1),
                    None,
                ),
            ],
        ),
        quarantine_time=timedelta(days=10),
    )

    mock_project_detail = mock.Mock(spec=model.ProjectDetail)

    with mock.patch(
        "simple_repository.components.new_releases_remover.NewReleasesRemover._exclude_recent_distributions",
        return_value=mock_project_detail,
    ) as mock_exclude_recent_distributions:
        project_page = await repository.get_project_page("project")

    mock_exclude_recent_distributions.assert_called_once()
    assert project_page == mock_project_detail
