import contextlib
import types
import typing

from simple_repository import model
from simple_repository.components.http import HttpRepository
from simple_repository.components.core import RepositoryContainer, SimpleRepository
from simple_repository.components.priority_selected import PrioritySelectedProjectsRepository
from simple_repository._typing_compat import override

import copy
import dataclasses

import asyncio

from simple_repository.model import RequestContext


class SimpleFileInjector(RepositoryContainer):
    # async def get_project_page(
    #     self,
    #     project_name: str,
    #     *,
    #     request_context: model.RequestContext = model.RequestContext.DEFAULT,
    # ) -> model.ProjectDetail:
    #     # TODO: Use super, not source. That way we can inject the right context automatically.
    #     project_page = await self.source.get_project_page(project_name, request_context=request_context)
    #     import functools
    #     files = copy.deepcopy(project_page.files)
    #
    #     for file in files:
    #         object.__setattr__(file, '_file_retriever', functools.partial(self._fetch_file, file._file_retriever))
    #         # print('Replaced: ', file._file_retriever)
    #
    #     project_page = dataclasses.replace(project_page, files=files)
    #     return project_page

    @classmethod
    async def _fetch_file(cls, upstream_file_retriever, *, request_context: RequestContext) -> bytes:
        # The type of upstream_file_retriever will be the same as this method, except it has already got the upstream_file_retriever partial. (probably need to be a partial)
        upstream = await upstream_file_retriever(request_context=request_context)
        return upstream + b'-' + b'g'

    @contextlib.asynccontextmanager
    async def get_file(
            self,
            file: typing.Union[model.File, model.AuxiliaryFile],
            *,
            request_context: RequestContext,
    ) -> types.AsyncGeneratorType[bytes, None]:
        # async with file._file_source.open(request_context=request_context) as source:
        #     yield source + b'-' + b'g'

        async with super().get_file(file, request_context=request_context) as source:
            yield source + b'-' + b'g'
        # # The type of upstream_file_retriever will be the same as this method, except it has already got the upstream_file_retriever partial. (probably need to be a partial)
        # upstream = await upstream_file_retriever(request_context=request_context)
        # return upstream + b'-' + b'g'

    # @contextlib.asynccontextmanager
    # async def fetch_resource(
    #         self,
    #
    #         file: model.File,  # possibly aux too?
    #         file_source: typing.Optional[model.File],
    #         request_context: model.RequestContext,
    # ):
    #     parent = repo_chain[-1]
    #     async with parent.fetch_resource(repo_chain[:-1], file, request_context=request_context) as response:
    #         # print('RESPONSE:', response.headers)
    #         print('RESPONSE:', response)
    #         yield response


async def main():
    repo = HttpRepository('https://pypi.org/simple')
    repo = SimpleFileInjector(repo)
    repo = PrioritySelectedProjectsRepository(sources=[repo, repo])
    simple_repo = await repo.get_project_page('simple-repository')
    f = simple_repo.files[0]

    aux = f.auxiliary_file('.metadata')

    print(f._source_chain)
    print('FILE URL?', f.url)

    f = aux

    async with f.open(request_context=None) as resp:
        # r = await resp.read()
        r = resp
        # print('RESULT:', await resp.read())
    # r = await f.read_bytes(request_context=None)  # Could be a context manager, to improve the quality of the API.  # type:ignore

    print(r)

    # print(r.decode())
    print(len(r))



asyncio.run(main())