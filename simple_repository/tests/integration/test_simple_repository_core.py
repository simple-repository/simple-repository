import pytest

from simple_repository import model
from simple_repository._typing_compat import override
from simple_repository.components.core import RepositoryContainer, SimpleRepository


class CustomSource(SimpleRepository):
    # Simulates a resource which exists.
    @override
    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.Resource:
        return model.TextResource('abc')


class FileExtender(RepositoryContainer):
    # Simulates the ability to extend a resource.
    @override
    async def get_resource(
            self,
            project_name: str,
            resource_name: str,
            *,
            request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.Resource:
        resource = await super().get_resource(
            project_name, resource_name,
            request_context=request_context,
        )
        if resource_name.endswith('.metadata'):
            return resource

        assert isinstance(resource, model.TextResource)
        assert resource.text == 'abc'
        return model.TextResource('abc-def')


class ResourceExtractor(RepositoryContainer):
    # Simulates the ability to produce derivative resources (e.g. metadata from a wheel).
    @override
    async def get_resource(
            self,
            project_name: str,
            resource_name: str,
            *,
            request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.Resource:
        if resource_name.endswith('.metadata'):
            parent_resource_name = resource_name[:-len('.metadata')]
            parent_resource = await self.get_resource(project_name, parent_resource_name, request_context=request_context)
            assert isinstance(parent_resource, model.TextResource)
            return model.TextResource(parent_resource.text[::-1])
        else:
            return await super().get_resource(
                project_name, resource_name,
                request_context=request_context,
            )


@pytest.mark.asyncio
async def test_resource_chaining_order():
    # A repository which implements resource derivative calculation (such as is possible with metadata injector), and then afterwards the original file is extended. The derivative shouldn't take into account the modified file.
    repo = FileExtender(
        ResourceExtractor(
            CustomSource(),
        ),
    )
    r = await repo.get_resource('foo', 'bar')
    assert isinstance(r, model.TextResource)
    assert r.text == 'abc-def'

    r = await repo.get_resource('foo', 'bar.metadata')
    assert isinstance(r, model.TextResource)
    assert r.text == 'cba'

    # If we switch the order of the components, the extractor should use the extended file.
    repo = ResourceExtractor(
        FileExtender(
            CustomSource(),
        ),
    )

    r = await repo.get_resource('foo', 'bar.metadata')
    assert isinstance(r, model.TextResource)
    assert r.text == 'fed-cba'
