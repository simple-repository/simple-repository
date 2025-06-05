# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import pytest

from ... import errors, model
from ...components.merged import MergedRepository
from .fake_repository import FakeRepository


@pytest.mark.asyncio
async def test_get_project_page() -> None:
    repo = MergedRepository(
        [
            FakeRepository(),
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        model.Meta('1.1'),
                        "numpy",
                        files=(
                            model.File("numpy-1.1.whl", "url1", {}, size=1),
                            model.File("numpy-1.2.whl", "url1", {}, size=1),
                        ),
                    ),
                ],
            ),
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        model.Meta('1.0'),
                        "numpy",
                        files=(
                            model.File("numpy-1.1.whl", "url2", {}),
                            model.File("numpy-1.3.whl", "url2", {}),
                        ),
                    ),
                ],
            ),
        ],
    )

    resp = await repo.get_project_page("numpy")

    assert resp == model.ProjectDetail(
        model.Meta('1.0'),
        "numpy",
        files=(
            model.File("numpy-1.1.whl", "url1", {}, size=1),
            model.File("numpy-1.2.whl", "url1", {}, size=1),
            model.File("numpy-1.3.whl", "url2", {}),
        ),
    )


@pytest.mark.asyncio
async def test_get_project_page__versions() -> None:
    repo = MergedRepository(
        [
            FakeRepository(),
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        model.Meta('1.1'),
                        "numpy",
                        files=(
                            model.File("numpy-1.1.whl", "url1", {}, size=1),
                            model.File("numpy-1.2.whl", "url1", {}, size=1),
                        ),
                        versions=frozenset({"1.1", "1.2"}),
                    ),
                ],
            ),
            FakeRepository(
                project_pages=[
                    model.ProjectDetail(
                        model.Meta('1.2'),
                        "numpy",
                        files=(
                            model.File("numpy-1.1.whl", "url2", {}, size=1),
                            model.File("numpy-1.3.whl", "url2", {}, size=1),
                        ),
                        versions=frozenset({"1.1", "1.3", "1.5"}),
                    ),
                ],
            ),
        ],
    )

    resp = await repo.get_project_page("numpy")

    assert resp == model.ProjectDetail(
        model.Meta('1.1'),
        "numpy",
        files=(
            model.File("numpy-1.1.whl", "url1", {}, size=1),
            model.File("numpy-1.2.whl", "url1", {}, size=1),
            model.File("numpy-1.3.whl", "url2", {}, size=1),
        ),
        versions=frozenset({"1.1", "1.2", "1.3", "1.5"}),
    )


@pytest.mark.asyncio
async def test_get_project_page_failed() -> None:
    repo = MergedRepository([
        FakeRepository(),
        FakeRepository(),
        FakeRepository(),
    ])

    with pytest.raises(
        errors.PackageNotFoundError,
        match="Package 'numpy' was not found in the configured source",
    ):
        await repo.get_project_page("numpy")
