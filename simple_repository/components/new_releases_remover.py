# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta
import typing

from .. import model
from .._typing_compat import override
from . import core


class NewReleasesRemover(core.RepositoryContainer):
    """
    A component used to remove newly released projects from the source
    repository until they have existed for the given quarantine time.
    This component can be used only if the source repository exposes the upload
    date according to PEP-700: https://peps.python.org/pep-0700/.
    """

    def __init__(
        self,
        source: core.SimpleRepository,
        quarantine_time: timedelta = timedelta(days=2),
        whitelist: typing.Tuple[str, ...] = (),
    ) -> None:
        self._quarantine_time = quarantine_time
        self._whitelist = whitelist
        super().__init__(source)

    @override
    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: typing.Optional[model.RequestContext] = None,
    ) -> model.ProjectDetail:
        project_page = await super().get_project_page(
            project_name,
            request_context=request_context,
        )

        if project_name in self._whitelist:
            return project_page

        return self._exclude_recent_distributions(
            project_page=project_page,
            now=datetime.now(),
        )

    def _exclude_recent_distributions(
        self,
        project_page: model.ProjectDetail,
        now: datetime,
    ) -> model.ProjectDetail:
        files_to_maintain = []
        files_to_be_removed: typing.List[typing.Tuple[model.File, datetime]] = []

        for file in project_page.files:
            if not file.upload_time:
                # We maintain the file if there is no upload time information.
                files_to_maintain.append(file)
            else:
                quarantine_release_time = file.upload_time + self._quarantine_time
                # Maintain the file if it has been available for longer than the quarantine time.
                if quarantine_release_time < now:
                    files_to_maintain.append(file)
                else:
                    files_to_be_removed.append((file, quarantine_release_time))

        date_format = "%Y-%m-%dT%H:%M:%SZ"
        serialized_quarantined_files = [
            {
                "filename": file.filename,
                "quarantine_release_time": quarantine_release_time.strftime(
                    date_format,
                ),
                "upload_time": typing.cast(datetime, file.upload_time).strftime(
                    date_format,
                ),
            }
            for file, quarantine_release_time in files_to_be_removed
        ]
        # Note that we don't remove the version from the versions list on project page.
        # PEP-700 states that we are allowed to have a release without any files in it.
        return dataclasses.replace(
            project_page,
            files=tuple(files_to_maintain),
            # Use a private attribute to give context of the files that have been quarantined.
            private_metadata=project_page.private_metadata
            | {
                "_quarantined_files": serialized_quarantined_files,
            },
        )
