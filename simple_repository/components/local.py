# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

from datetime import datetime
import os
import pathlib
import typing

import packaging.utils

from .. import errors, model, utils
from .._typing_compat import override
from . import core


class LocalRepository(core.SimpleRepository):
    """
    Creates a simple repository from a local directory.
    The directory must contain a subdirectory for each project,
    named as the normalized project name. Each subdirectory will
    contain the distributions associated with that project.
    Each file in a project page is mapped to a URL with the
    following structure: file:// index_path / project_name / file_name.
    """

    def __init__(
        self,
        index_path: pathlib.Path,
    ) -> None:
        if not index_path.is_dir():
            raise ValueError("index_path must be a directory")
        self._index_path = index_path.resolve()

    @override
    async def get_project_list(
        self,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.ProjectList:
        return model.ProjectList(
            meta=model.Meta("1.0"),
            projects=frozenset(
                model.ProjectListElement(x.name)
                for x in self._index_path.iterdir()
                if x.is_dir() and x.name == packaging.utils.canonicalize_name(x.name)
            ),
        )

    @override
    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.ProjectDetail:
        project_dir = (self._index_path / project_name).resolve()
        if not project_dir.is_dir():
            raise errors.PackageNotFoundError(project_name)

        files = []
        for file in sorted(project_dir.iterdir()):
            if not file.is_file():
                continue
            file_stat = os.stat(file)
            files.append(
                model.File(
                    filename=file.name,
                    url=f"file://{file.resolve()}",
                    hashes={},
                    upload_time=datetime.utcfromtimestamp(
                        file_stat.st_mtime,
                    ),
                    size=file_stat.st_size,
                ),
            )

        return model.ProjectDetail(
            meta=model.Meta("1.1"),
            name=project_name,
            files=tuple(files),
        )

    @override
    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.Resource:
        repository_uri = (self._index_path / project_name).resolve()
        resource_uri = (repository_uri / resource_name).resolve()

        # Validate both paths for security (path traversal prevention)
        if not utils.is_relative_to(
            repository_uri,
            self._index_path,
        ) or not utils.is_relative_to(resource_uri, repository_uri):
            raise ValueError(
                f"{resource_uri} is not contained in {repository_uri}",
            )

        # Check if project directory exists
        if not repository_uri.is_dir():
            raise errors.PackageNotFoundError(project_name)

        # Check if resource file exists
        if not resource_uri.is_file():
            raise errors.ResourceUnavailable(resource_name)

        # Calculating on the fly the hash of the whole package can be too slow.
        # "mtime + size" provide a good approximation to detect if the package has been changed.
        etag_base = (
            str(resource_uri.stat().st_mtime) + "-" + str(resource_uri.stat().st_size)
        )
        digest = utils.hash_md5(etag_base.encode())
        etag = f'"{digest}"'

        return model.LocalResource(
            path=resource_uri,
            to_cache=False,  # Prevent caching of locally stored resources.
            context=model.Context(etag=etag),
        )
