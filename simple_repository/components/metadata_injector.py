# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import dataclasses
import pathlib
import re
import tempfile
import typing
import zipfile

import httpx
import packaging.utils

from .. import errors, model, utils
from .._typing_compat import override
from . import core

metadata_regex = re.compile(r"^(.*)-.*\.dist-info/METADATA$")


class MetadataInjectorRepository(core.RepositoryContainer):
    """Adds PEP-658 support to a simple repository. If not already specified,
    sets the dist-info metadata for all wheels packages in a project page.
    Metadata is extracted from the wheels on the fly and cached for later use.
    """

    def __init__(
        self,
        source: core.SimpleRepository,
        http_client: typing.Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._http_client = http_client or httpx.AsyncClient()
        super().__init__(source)

    @override
    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.ProjectDetail:
        return self._add_metadata_attribute(
            await super().get_project_page(
                project_name,
                request_context=request_context,
            ),
        )

    @override
    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
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

        # Get hold of the actual artefact from which we want to extract
        # the metadata.
        resource = await self.get_resource(
            project_name,
            utils.remove_suffix(resource_name, ".metadata"),
            request_context=request_context,
        )
        if isinstance(resource, model.HttpResource):
            try:
                metadata = await self._download_metadata(
                    package_name=utils.remove_suffix(resource_name, ".metadata"),
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
                utils.remove_suffix(resource_name, ".metadata"),
                "Unable to fetch the resource needed to extract the metadata.",
            )

        metadata_resource = model.TextResource(
            text=metadata,
        )
        etag = resource.context.get("etag")
        if etag:
            # Use the same etag as the one that identifies the package.
            # In this way, if that package changes, also the metadata will be invalidated.
            metadata_resource.context["etag"] = etag
        return metadata_resource

    def _get_metadata_from_wheel(self, package_path: pathlib.Path) -> str:
        package_tokens = package_path.name.split("-")
        if len(package_tokens) < 2:
            raise ValueError(
                f"Filename {package_path.name} is not normalized according to PEP-427",
            )
        distribution = packaging.utils.canonicalize_name(package_tokens[0])
        # Package consumer, when extracting metadata, should tolerate small differences
        # respecting what is strictly described in PEP-427, for reference see:
        # https://packaging.python.org/en/latest/specifications/binary-distribution-format/
        try:
            with zipfile.ZipFile(package_path, "r") as ziparchive:
                for file in ziparchive.namelist():
                    match = metadata_regex.match(file)
                    if not match:
                        continue
                    if (
                        packaging.utils.canonicalize_name(match.group(1))
                        == distribution
                    ):
                        return ziparchive.read(file).decode()
                raise errors.InvalidPackageError(
                    "Provided wheel doesn't contain a metadata file.",
                )
        except (zipfile.BadZipFile, zipfile.LargeZipFile) as e:
            raise errors.InvalidPackageError(
                "Unable to decompress the provided wheel.",
            ) from e

    def _get_metadata_from_package(self, package_path: pathlib.Path) -> str:
        if package_path.name.endswith(".whl"):
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
            if (
                file.url
                and file.filename.endswith(".whl")
                and not file.dist_info_metadata
            ):
                file = dataclasses.replace(file, dist_info_metadata=True)
            files.append(file)
        project_page = dataclasses.replace(project_page, files=tuple(files))
        return project_page
