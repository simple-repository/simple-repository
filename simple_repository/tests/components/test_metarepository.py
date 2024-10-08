# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import pytest

from ... import model
from ...components import core
from .fake_repository import FakeRepository


class TestClass(metaclass=core.SimpleRepositoryMeta):
    async def get_project_page(self, *, request_context: model.RequestContext = model.RequestContext.DEFAULT) -> model.RequestContext:
        return request_context

    async def get_project_list(self, *, request_context: model.RequestContext = model.RequestContext.DEFAULT) -> model.RequestContext:
        return request_context

    async def get_resource(self, *, request_context: model.RequestContext = model.RequestContext.DEFAULT) -> model.RequestContext:
        return request_context


@pytest.mark.asyncio
async def test_decorated_get_project_page__default_context() -> None:
    test_object = TestClass()
    context = await test_object.get_project_page()
    assert context != model.RequestContext.DEFAULT
    assert isinstance(context, model.RequestContext)
    assert context.repository is test_object  # type: ignore[comparison-overlap]


@pytest.mark.asyncio
async def test_decorated_get_project_page__passed_context() -> None:
    test_object = TestClass()
    request_context = model.RequestContext(
        repository=FakeRepository(),
    )
    context = await test_object.get_project_page(request_context=request_context)
    assert context is request_context


@pytest.mark.asyncio
async def test_decorated_get_project_list__default_context() -> None:
    test_object = TestClass()
    context = await test_object.get_project_list()
    assert context != model.RequestContext.DEFAULT
    assert context.repository is test_object  # type: ignore[comparison-overlap]


@pytest.mark.asyncio
async def test_decorated_get_project_list__passed_context() -> None:
    test_object = TestClass()
    request_context = model.RequestContext(
        repository=FakeRepository(),
    )
    context = await test_object.get_project_list(request_context=request_context)
    assert context is request_context


@pytest.mark.asyncio
async def test_decorated_get_resource__default_context() -> None:
    test_object = TestClass()
    context = await test_object.get_resource()
    assert context != model.RequestContext.DEFAULT
    assert isinstance(context, model.RequestContext)
    assert context.repository is test_object  # type: ignore[comparison-overlap]


@pytest.mark.asyncio
async def test_decorated_get_resource__passed_context() -> None:
    test_object = TestClass()
    request_context = model.RequestContext(
        repository=FakeRepository(),
    )
    context = await test_object.get_resource(request_context=request_context)
    assert context is request_context
