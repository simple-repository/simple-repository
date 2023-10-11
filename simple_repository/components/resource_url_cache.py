# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import aiosqlite

from .. import model
from ..ttl_cache import TTLDatabaseCache
from .core import RepositoryContainer, SimpleRepository


class ResourceURLCacheRepository(RepositoryContainer):
    """Caches urls provided by the source repository in the project pages.
    The cached URLs are used by the get_resource method to retrieve the
    URL associated with the requested resource without having to fetch
    it from the source repository.
    """
    def __init__(
        self,
        source: SimpleRepository,
        database: aiosqlite.Connection,
        ttl_min: int = 1,
        table_name: str = "url_cache",
    ) -> None:
        super().__init__(source)
        self._cache = TTLDatabaseCache(database, ttl_min, table_name)

    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectDetail:
        project_page = await super().get_project_page(
            project_name,
            request_context=request_context,
        )

        await self._cache.update(
            {f"{project_name}/{file.filename}": file.url for file in project_page.files},
        )
        return project_page

    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.Resource:
        if url := await self._cache.get(project_name + '/' + resource_name):
            return model.HttpResource(url=url)
        return await self.source.get_resource(
            project_name,
            resource_name,
            request_context=request_context,
        )
