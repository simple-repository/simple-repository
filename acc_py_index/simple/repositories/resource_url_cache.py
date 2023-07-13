import sqlite3

from ...ttl_cache import TTLDatabaseCache
from ..model import HttpResource, ProjectDetail, Resource
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
        database: sqlite3.Connection,
        ttl_min: int = 1,
        table_name: str = "url_cache",
    ) -> None:
        super().__init__(source)
        self._cache = TTLDatabaseCache(database, ttl_min, table_name)

    async def get_project_page(self, project_name: str) -> ProjectDetail:
        project_page = await super().get_project_page(project_name)

        self._cache.update(
            {f"{project_name}/{file.filename}": file.url for file in project_page.files},
        )
        return project_page

    async def get_resource(self, project_name: str, resource_name: str) -> Resource:
        if url := self._cache.get(project_name + '/' + resource_name):
            return HttpResource(url=url)
        return await self.source.get_resource(project_name, resource_name)
