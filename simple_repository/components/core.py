# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import contextlib
import dataclasses
import typing

from .. import model
from .._typing_compat import override

if typing.TYPE_CHECKING:
    from .._typing_compat import TypeAlias
    WrappedFunction: TypeAlias = typing.Callable[..., typing.Any]


class SimpleRepository:
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

    @contextlib.asynccontextmanager
    async def get_file(
            self,
            file: typing.Union[model.File, model.AuxilliaryFile],  # possibly aux too?
            # file_source: typing.Optional[model.File],
            # repo_chain: typing.Tuple[SimpleRepository, ...],
            # file: typing.Union[model.File, model.AuxilliaryFile],
            request_context: model.RequestContext,
    ):
        raise NotImplementedError()

    setattr(get_file, '_is_overridden', False)

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
    # TODO: Write a guide on when to call `self.source.get_*`, `super().get_*` and `self.get_*`
    def __init__(self, source: SimpleRepository) -> None:
        self.source = source

    @override
    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectDetail:
        detail = await self.source.get_project_page(project_name, request_context=request_context)
        return self._setup_file_retrieval(detail)

    def _setup_file_retrieval(self, detail: model.ProjectDetail) -> model.ProjectDetail:
        # If a suitable implementation exists, ensure that the result of fetching the bytes of a
        # File goes through this repository's method.
        if getattr(type(self).get_file, '_is_overridden', True):
            files = []
            for original_file in detail.files:
                # Drop the url (and implicitly take a copy), since the URL won't reflect the
                # original file any more.
                file = dataclasses.replace(
                    original_file,
                    url=None,
                    file_source=original_file,
                    originating_repository=self,
                )
                files.append(file)

            detail = dataclasses.replace(detail, files=tuple(files))

        return detail

    @contextlib.asynccontextmanager
    async def get_file(
        self,
        file: typing.Union[model.File, model.AuxiliaryFile],
        request_context: model.RequestContext,
    ):
        # Note that we don't use self.source here... the chain of repositories comes from the File
        # definition.

        if file.originating_repository is not self:
            # TODO: This might be quite unreasonable if the terminating repository doesn't modify
            #  the file. Perhaps we should be walking the repository children to confirm this error.
            raise ValueError("The file you are trying to get does not belong to the repository")
        file_source = file.file_source
        assert file_source is not None  # RepositoryContainers are always going to produce Files
        # with a file_source.
        async with file_source.originating_repository.get_file(
                file_source,
                request_context=request_context,
        ) as response:
            yield response

    get_file._is_overridden = False

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
