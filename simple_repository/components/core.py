# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import functools
import typing

from .. import model


class SimpleRepositoryMeta(type):
    # A metaclass that swaps model.RequestContext.DEFAULT arguments for RequestContext
    # instances containing the repository upon which the method is called.
    def __new__(
            cls: typing.Type[type],
            name: str,
            bases: tuple[typing.Type[type]],
            namespace: dict[str, typing.Any],
    ) -> typing.Type[type]:
        wrapped_fn: typing.TypeAlias = typing.Callable[[typing.Any], typing.Any]

        def dec(fn: wrapped_fn) -> wrapped_fn:
            @functools.wraps(fn)
            async def wrapper(
                    self: typing.Any, *args: typing.Any, **kwargs: typing.Any,
            ) -> typing.Any:
                # If we have the default RequestContext (which is None), swap it for
                # a new context which contains self.
                if kwargs.get('request_context') is model.RequestContext.DEFAULT:
                    kwargs['request_context'] = model.RequestContext(self)
                return await fn(self, *args, **kwargs)
            return wrapper

        if 'get_project_page' in namespace:
            namespace['get_project_page'] = dec(namespace['get_project_page'])
        if 'get_project_list' in namespace:
            namespace['get_project_list'] = dec(namespace['get_project_list'])
        if 'get_resource' in namespace:
            namespace['get_resource'] = dec(namespace['get_resource'])

        result = type.__new__(cls, name, bases, dict(namespace))
        return result


class SimpleRepository(metaclass=SimpleRepositoryMeta):
    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectDetail:
        raise NotImplementedError()

    async def get_project_list(
        self,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectList:
        raise NotImplementedError()

    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.Resource:
        raise NotImplementedError()


class RepositoryContainer(SimpleRepository):
    """A base class for components that enhance the functionality of a source
    `SimpleRepository`. If not overridden, the methods provided by this class
    will delegate to the corresponding methods of the source repository.
    """
    def __init__(self, source: SimpleRepository) -> None:
        self.source = source

    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectDetail:
        return await self.source.get_project_page(project_name, request_context=request_context)

    async def get_project_list(
        self,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectList:
        return await self.source.get_project_list(request_context=request_context)

    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.Resource:
        return await self.source.get_resource(
            project_name,
            resource_name,
            request_context=request_context,
        )
