# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import functools
import typing

from .. import model
from .._typing_compat import override

if typing.TYPE_CHECKING:
    from .._typing_compat import TypeAlias
    WrappedFunction: TypeAlias = typing.Callable[..., typing.Any]


class SimpleRepositoryMeta(type):
    # A metaclass that swaps model.RequestContext.DEFAULT arguments for RequestContext
    # instances containing the repository upon which the method is called.
    def __new__(
            cls: typing.Type[type],
            name: str,
            bases: typing.Tuple[typing.Type[type]],
            namespace: typing.Dict[str, typing.Any],
    ) -> typing.Type[type]:

        def dec(fn: WrappedFunction) -> WrappedFunction:
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
        """
        Get the project detail page of the given project

        The resulting project detail includes resources available for the
        project. These resources MUST be requested through the
        :meth:`get_resource` method, as the `model.File` resources may not be
        available through a URL.

        Parameters
        ----------
        project_name:
            The name of the project, which is not normalized.
        request_context:
            Additional meta information about the request being made. An example
            of such information is providing cache/ETag metadata to allow the
            repository to raise :class:`model.NotModified`.

        Returns
        -------
        model.ProjectDetail:
            The project detail content of the requested project

        Raises
        ------
        errors.PackageNotFoundError:
            If the project is not available in the repository.
        model.NotModified:
            When sufficient request context is provided, it is possible for the
            repository to raise a NotModified exception to indicate that the
            result that corresponds to the given cache headers is still valid.
        errors.UnsupportedSerialization:
            When the upstream repository is providing information that is not
            processable.
        errors.SourceRepositoryUnavailable:
            When the upstream repository is not available.
        """
        raise NotImplementedError()

    async def get_project_list(
        self,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectList:
        """
        Get the list of projects available in the repository.

        Parameters
        ----------
        request_context:
            Additional meta information about the request being made. An example
            of such information is providing cache/ETag metadata to allow the
            repository to raise :class:`model.NotModified`.

        Returns
        -------
        A list of all projects available on the repository.

        Raises
        ------
        model.NotModified:
            When sufficient request context is provided, it is possible for the
            repository to raise a NotModified exception to indicate that the
            result that corresponds to the given cache headers is still valid.
        errors.UnsupportedSerialization:
            When the upstream repository is providing information that is not
            processable.
        errors.SourceRepositoryUnavailable:
            When the upstream repository is not available.

        Notes
        -----
        It is technically possible for projects to be accessible
        from :meth:`get_project_page` which are not in list provided by this
        method.

        """
        raise NotImplementedError()

    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.Resource:
        """
        Fetch a project detail resource from the repository

        Whilst this method is not part of the PEP-503 specification directly,
        this method exists such that resource requests can be processed by a
        repository component. Examples of useful processing that can happen
        include the computation of metadata upon request, and the ability to
        log specific requests.

        Parameters
        ----------
        project_name:
            The name of the project for which the resource is being requested.
        resource_name:
            The filename of the resource, as given by the ProjectDetail content.
        request_context:
            Additional meta information about the request being made. An example
            of such information is providing cache/ETag metadata to allow the
            repository to raise :class:`model.NotModified`.

        Raises
        ------
        error.ResourceUnavailable:
            When no such resource exists.
        model.NotModified:
            When sufficient request context is provided, it is possible for the
            repository to raise a NotModified exception to indicate that the
            result that corresponds to the given cache headers is still valid.
        errors.SourceRepositoryUnavailable:
            When the upstream repository is not available.

        """
        raise NotImplementedError()


class RepositoryContainer(SimpleRepository):
    """A base class for components that enhance the functionality of a source
    `SimpleRepository`. If not overridden, the methods provided by this class
    will delegate to the corresponding methods of the source repository.
    """
    def __init__(self, source: SimpleRepository) -> None:
        self.source = source

    @override
    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectDetail:
        return await self.source.get_project_page(project_name, request_context=request_context)

    @override
    async def get_project_list(
        self,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectList:
        return await self.source.get_project_list(request_context=request_context)

    @override
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
