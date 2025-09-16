# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import pytest

from ... import errors, model
from ...components.core import RepositoryContainer
from .fake_repository import FakeRepository


@pytest.mark.asyncio
async def test_get_project_page() -> None:
    repository = RepositoryContainer(
        FakeRepository(
            project_pages=[
                model.ProjectDetail(model.Meta("1.0"), "numpy", files=()),
            ],
        ),
    )
    result = await repository.get_project_page("numpy")
    assert result == model.ProjectDetail(model.Meta("1.0"), "numpy", files=())
    with pytest.raises(errors.PackageNotFoundError):
        await repository.get_project_page("pandas")


@pytest.mark.asyncio
async def test_get_project_list() -> None:
    repository = RepositoryContainer(
        FakeRepository(
            project_list=model.ProjectList(
                meta=model.Meta("1.0"),
                projects=frozenset([model.ProjectListElement("numpy")]),
            ),
        ),
    )
    result = await repository.get_project_list()
    assert result.projects == frozenset([model.ProjectListElement("numpy")])


@pytest.mark.asyncio
async def test_get_resource() -> None:
    repository = RepositoryContainer(
        FakeRepository(
            project_pages=[
                model.ProjectDetail(model.Meta("1.0"), "numpy", files=()),
            ],
            resources={
                "numpy.whl": model.HttpResource("numpy_url"),
            },
        ),
    )
    result = await repository.get_resource("numpy", "numpy.whl")
    assert isinstance(result, model.HttpResource)
    assert result.url == "numpy_url"
