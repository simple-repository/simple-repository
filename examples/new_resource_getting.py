import asyncio
import contextlib
import types
import typing

from simple_repository import model
from simple_repository.components.core import RepositoryContainer
from simple_repository.components.http import HttpRepository
from simple_repository.components.priority_selected import PrioritySelectedProjectsRepository
from simple_repository.model import RequestContext


class SimpleFileInjector(RepositoryContainer):
    @contextlib.asynccontextmanager
    async def get_file(
            self,
            file: typing.Union[model.File, model.AuxiliaryFile],
            *,
            request_context: RequestContext,
    ) -> types.AsyncGeneratorType[bytes, None]:
        # async with file._file_source.open(request_context=request_context) as source:
        #     yield source + b'-' + b'g'

        # We can get the full file:
        if isinstance(file, model.AuxiliaryFile):
            async with file.file.open() as resp:
                print('Got it:', len(resp))
                pass

        async with super().get_file(file, request_context=request_context) as source:
            yield source + b'-' + b'g'


async def main():
    repo = HttpRepository('https://pypi.org/simple')
    repo = SimpleFileInjector(repo)
    repo = PrioritySelectedProjectsRepository(sources=[repo, repo])
    simple_repo = await repo.get_project_page('simple-repository')
    f = simple_repo.files[0]

    aux = f.auxiliary_file('.metadata')

    print('FILE URL?', f.url)

    f = aux

    file = f
    while True:

        print(file.originating_repository)
        print(file)
        file = file.file_source
        if file is None:
            break

    async with f.open(request_context=None) as resp:
        # r = await resp.read()
        r = resp
        # print('RESULT:', await resp.read())

    print(r)

    # print(r.decode())
    print(len(r))

asyncio.run(main())
