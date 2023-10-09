import pytest

from acc_py_index.simple.model import RequestContext
from acc_py_index.simple.repositories.core import SimpleRepositoryMeta

from .fake_repository import FakeRepository


class TestClass(metaclass=SimpleRepositoryMeta):
    async def get_project_page(self, *, request_context: RequestContext = RequestContext.DEFAULT) -> RequestContext:
        return request_context

    async def get_project_list(self, *, request_context: RequestContext = RequestContext.DEFAULT) -> RequestContext:
        return request_context

    async def get_resource(self, *, request_context: RequestContext = RequestContext.DEFAULT) -> RequestContext:
        return request_context


@pytest.mark.asyncio
async def test_decorated_get_project_page__default() -> None:
    test_object = TestClass()
    context = await test_object.get_project_page()
    assert context != RequestContext.DEFAULT
    assert context == RequestContext(repository=test_object)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_decorated_get_project_page() -> None:
    test_object = TestClass()
    request_context = RequestContext(
        repository=FakeRepository(),
    )
    context = await test_object.get_project_page(request_context=request_context)
    assert context == request_context


@pytest.mark.asyncio
async def test_decorated_get_project_list__default() -> None:
    test_object = TestClass()
    context = await test_object.get_project_list()
    assert context != RequestContext.DEFAULT
    assert context == RequestContext(repository=test_object)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_decorated_get_project_list() -> None:
    test_object = TestClass()
    request_context = RequestContext(
        repository=FakeRepository(),
    )
    context = await test_object.get_project_list(request_context=request_context)
    assert context == request_context


@pytest.mark.asyncio
async def test_decorated_get_resource__default() -> None:
    test_object = TestClass()
    context = await test_object.get_resource()
    assert context != RequestContext.DEFAULT
    assert context == RequestContext(repository=test_object)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_decorated_get_resource() -> None:
    test_object = TestClass()
    request_context = RequestContext(
        repository=FakeRepository(),
    )
    context = await test_object.get_resource(request_context=request_context)
    assert context == request_context
