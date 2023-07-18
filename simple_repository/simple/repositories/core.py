# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from typing import Protocol

from ..model import ProjectDetail, ProjectList, Resource


class SimpleRepository(Protocol):
    async def get_project_page(self, project_name: str) -> ProjectDetail:
        ...

    async def get_project_list(self) -> ProjectList:
        ...

    async def get_resource(self, project_name: str, resource_name: str) -> Resource:
        ...


class RepositoryContainer(SimpleRepository):
    """A base class for components that enhance the functionality of a source
    `SimpleRepository`. If not overridden, the methods provided by this class
    will delegate to the corresponding methods of the source repository.
    """
    def __init__(self, source: SimpleRepository) -> None:
        self.source = source

    async def get_project_page(self, project_name: str) -> ProjectDetail:
        return await self.source.get_project_page(project_name)

    async def get_project_list(self) -> ProjectList:
        return await self.source.get_project_list()

    async def get_resource(self, project_name: str, resource_name: str) -> Resource:
        return await self.source.get_resource(project_name, resource_name)
