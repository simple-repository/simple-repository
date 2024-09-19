from __future__ import annotations

import pytest

from ... import model
from .fake_repository import FakeRepository


@pytest.fixture
def source_repository() -> FakeRepository:
    return FakeRepository(
        project_list=model.ProjectList(
            meta=model.Meta("1.0"),
            projects=frozenset([
                model.ProjectListElement("project1"),
                model.ProjectListElement("project2"),
                model.ProjectListElement("project3"),
            ]),
        ),
        project_pages=[
            model.ProjectDetail(
                meta=model.Meta("1.0"),
                name="project1",
                files=(),
            ),
            model.ProjectDetail(
                meta=model.Meta("1.0"),
                name="project2",
                files=(),
            ),
            model.ProjectDetail(
                meta=model.Meta("1.0"),
                name="project3",
                files=(),
            ),
        ],
        resources={
            "project1-1.0.tar.gz": model.HttpResource("content1"),
            "project2-1.0.tar.gz": model.HttpResource("content2"),
            "project3-1.0.tar.gz": model.HttpResource("content3"),
        },
    )
