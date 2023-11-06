# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from dataclasses import replace
import pathlib
import re
import tempfile
import zipfile

import aiosqlite
import httpx
from packaging.utils import canonicalize_name

from .. import errors, model, ttl_cache, utils
from .core import RepositoryContainer, SimpleRepository

metadata_regex = re.compile(r'^(.*)-.*\.dist-info/METADATA$')


class MetadataInjectorRepository(RepositoryContainer):
    """Adds PEP-658 support to a simple repository. If not already specified,
    sets the dist-info metadata for all wheels packages in a project page.
    Metadata is extracted from the wheels on the fly and cached for later use.
    """
    def __init__(
        self,
        source: SimpleRepository,
        database: aiosqlite.Connection,
        http_client: httpx.AsyncClient | None = None,
        ttl_days: int = 7,
        table_name: str = "metadata_cache",
    ) -> None:
        self._http_client = http_client or httpx.AsyncClient()
        self._cache = ttl_cache.TTLDatabaseCache(
            database=database,
            ttl_seconds=ttl_days * 60 * 60 * 24,
            table_name=table_name,
        )
        super().__init__(source)

    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectDetail:
        return self._add_metadata_attribute(
            await super().get_project_page(project_name, request_context=request_context),
        )

    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.Resource:
        try:
            # Attempt to get the resource from upstream.
            return await super().get_resource(
                project_name,
                resource_name,
                request_context=request_context,
            )
        except errors.ResourceUnavailable:
            if not resource_name.endswith(".metadata"):
                # If we tried to get a resource that wasn't a .metadata one, and it failed,
                # propagate the error.
                raise

        # The resource doesn't exist upstream, and looks like a metadata file has been
        # requested. Let's try to fetch the underlying resource and compute the metadata.

        # First, let's attempt to get the metadata out of the cache.
        metadata = await self._cache.get(project_name + "/" + resource_name)
        if not metadata:
            # Get hold of the actual artefact from which we want to extract
            # the metadata.
            resource = await request_context.repository.get_resource(
                project_name, resource_name.removesuffix(".metadata"),
                request_context=request_context,
            )
            if isinstance(resource, model.HttpResource):
                try:
                    metadata = await self._download_metadata(
                        package_name=resource_name.removesuffix(".metadata"),
                        download_url=resource.url,
                        http_client=self._http_client,
                    )
                except ValueError as e:
                    # If we can't get hold of the metadata from the file then raise
                    # a resource unavailable.
                    raise errors.ResourceUnavailable(resource_name) from e
            elif isinstance(resource, model.LocalResource):
                try:
                    metadata = self._get_metadata_from_package(resource.path)
                except ValueError as e:
                    raise errors.ResourceUnavailable(resource_name) from e
            else:
                raise errors.ResourceUnavailable(
                    resource_name.removesuffix(".metadata"),
                    "Unable to fetch the resource needed to extract the metadata.",
                )

            # Cache the result for a faster response in the future.
            await self._cache.set(project_name + "/" + resource_name, metadata)

        return model.TextResource(
            text=metadata,
        )

    def _get_metadata_from_wheel(self, package_path: pathlib.Path) -> str:
        package_tokens = package_path.name.split('-')
        if len(package_tokens) < 2:
            raise ValueError(
                f"Filename {package_path.name} is not normalized according to PEP-427",
            )
        distribution = canonicalize_name(package_tokens[0])
        # Package consumer, when extracting metadata, should tolerate small differences
        # respecting what is strictly described in PEP-427, for reference see:
        # https://packaging.python.org/en/latest/specifications/binary-distribution-format/
        try:
            with zipfile.ZipFile(package_path, 'r') as ziparchive:
                for file in ziparchive.namelist():
                    if not (match := metadata_regex.match(file)):
                        continue
                    if canonicalize_name(match.group(1)) == distribution:
                        return ziparchive.read(file).decode()
                raise errors.InvalidPackageError(
                    "Provided wheel doesn't contain a metadata file.",
                )
        except (zipfile.BadZipFile, zipfile.LargeZipFile) as e:
            raise errors.InvalidPackageError(
                "Unable to decompress the provided wheel.",
            ) from e

    def _get_metadata_from_package(self, package_path: pathlib.Path) -> str:
        if package_path.name.endswith('.whl'):
            return self._get_metadata_from_wheel(package_path)
        raise ValueError("Package provided is not a wheel")

    async def _download_metadata(
        self,
        package_name: str,
        download_url: str,
        http_client: httpx.AsyncClient,
    ) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_path = pathlib.Path(tmpdir) / package_name
            await utils.download_file(download_url, pkg_path, http_client)
            return self._get_metadata_from_package(pkg_path)

    def _add_metadata_attribute(
        self,
        project_page: model.ProjectDetail,
    ) -> model.ProjectDetail:
        """Add the data-core-metadata to all the packages distributed as wheels"""
        files = []
        for file in project_page.files:
            if file.url and file.filename.endswith(".whl") and not file.dist_info_metadata:
                file = replace(file, dist_info_metadata=True)
            files.append(file)
        project_page = replace(project_page, files=tuple(files))
        return project_page
