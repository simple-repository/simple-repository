import pathlib
import sqlite3
import tempfile
import zipfile

import aiohttp

from .. import cache, errors, utils
from .model import ProjectDetail, Resource, ResourceType
from .repositories import RepositoryContainer, SimpleRepository


def get_metadata_from_wheel(package_path: pathlib.Path, package_name: str) -> str:
    package_tokens = package_name.split('-')
    if len(package_tokens) < 2:
        raise ValueError(
            f"Package name {package_name} is not normalized according to PEP-427",
        )
    name_ver = package_tokens[0] + '-' + package_tokens[1]

    try:
        with zipfile.ZipFile(package_path, 'r') as ziparchive:
            try:
                return ziparchive.read(name_ver + ".dist-info/METADATA").decode()
            except KeyError as e:
                raise errors.InvalidPackageError(
                    "Provided wheel doesn't contain a metadata file.",
                ) from e
    except (zipfile.BadZipFile, zipfile.LargeZipFile) as e:
        raise errors.InvalidPackageError(
            "Unable to decompress the provided wheel.",
        ) from e


def get_metadata_from_package(package_path: pathlib.Path, package_name: str) -> str:
    if package_name.endswith('.whl'):
        return get_metadata_from_wheel(package_path, package_name)
    raise ValueError("Package provided is not a wheel")


async def download_metadata(
    package_name: str,
    download_url: str,
    session: aiohttp.ClientSession,
) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = pathlib.Path(tmpdir) / package_name
        await utils.download_file(download_url, pkg_path, session)
        return get_metadata_from_package(pkg_path, package_name)


def add_metadata_attribute(project_page: ProjectDetail) -> ProjectDetail:
    """Add the data-dist-info-metadata to all the packages distributed as wheels"""
    for file in project_page.files:
        if file.url and file.filename.endswith(".whl") and file.dist_info_metadata is None:
            file.dist_info_metadata = True
    return project_page


class MetadataInjectorRepository(RepositoryContainer):
    """Adds PEP-658 support to a simple repository. If not already specified,
    sets the dist-info metadata for all wheels packages in a project page.
    Metadata is extracted from the wheels on the fly and cached for later use.
    """
    def __init__(
        self,
        source: SimpleRepository,
        database: sqlite3.Connection,
        session: aiohttp.ClientSession,
        ttl_days: int = 7,
        table_name: str = "metadata_cache",
    ) -> None:
        self._session = session
        self._cache = cache.TTLDatabaseCache(
            database=database,
            ttl_seconds=ttl_days * 60 * 60 * 24,
            table_name=table_name,
        )
        super().__init__(source)

    async def get_project_page(self, project_name: str) -> ProjectDetail:
        return add_metadata_attribute(
            await super().get_project_page(project_name),
        )

    async def get_resource(self, project_name: str, resource_name: str) -> Resource:
        # Attempt to get the resource from upstream.
        try:
            return await super().get_resource(project_name, resource_name)
        except errors.ResourceUnavailable:
            if not resource_name.endswith(".metadata"):
                # If we tried to get a resource that wasn't a .metadata one and it failed,
                # propagate it. Otherwise, we move on to trying to handle metadata files not
                # available in the source.
                raise

        # The resource doesn't exist upstream, and ends with .metadata - let's try to
        # fetch the underlying resource and compute the metadata.

        # First, let's attempt to get the metadata out of the cache.
        metadata = self._cache.get(project_name + "/" + resource_name)

        if not metadata:
            # Get hold of the actual artefact from which we want to extract
            # the metadata.
            resource = await super().get_resource(
                project_name, resource_name.removesuffix(".metadata"),
            )
            if resource.type != ResourceType.REMOTE_RESOURCE:
                raise errors.ResourceUnavailable(
                    resource_name.removesuffix(".metadata"),
                    "Unable to fetch the resource needed to extract the metadata.",
                )
            try:
                metadata = await download_metadata(
                    package_name=resource_name.removesuffix(".metadata"),
                    download_url=resource.value,
                    session=self._session,
                )
            except ValueError as e:
                # If we can't get hold of the metadata from the file then raise
                # a resource unavailable.
                raise errors.ResourceUnavailable(resource_name) from e

            # Cache the result for a faster response in the future.
            self._cache[project_name + "/" + resource_name] = metadata

        return Resource(
            value=metadata,
            type=ResourceType.METADATA,
        )
