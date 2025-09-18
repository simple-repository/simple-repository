# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import typing

import pytest

from ... import model
from ...components.yanking import YankProvider, YankRepository
from .fake_repository import FakeRepository


class FakeYankProvider(YankProvider):
    async def yanked_versions(
        self,
        project_page: model.ProjectDetail,
    ) -> typing.Dict[str, str]:
        return {"1.0": "reason"}

    async def yanked_files(
        self,
        project_page: model.ProjectDetail,
    ) -> typing.Dict[str, str]:
        return {"project-1.0-any.whl": "reason"}


@pytest.fixture
def project_page() -> model.ProjectDetail:
    return model.ProjectDetail(
        model.Meta("1.0"),
        name="project",
        files=(
            model.File("project-1.0-any.whl", "url", {}),
            model.File("project-1.0.tar.gz", "url", {}),
            model.File("project-1.1.tar.gz", "url", {}),
        ),
    )


@pytest.fixture
def repository(project_page: model.ProjectDetail) -> YankRepository:
    source = FakeRepository(
        project_pages=[project_page],
    )
    provider = FakeYankProvider()

    return YankRepository(
        source=source,
        yank_provider=provider,
    )


@pytest.mark.asyncio
async def test_get_project_page(repository: YankRepository) -> None:
    result = await repository.get_project_page("project")

    assert result.files[0].yanked == "reason"
    assert result.files[1].yanked == "reason"
    assert result.files[2].yanked is None
