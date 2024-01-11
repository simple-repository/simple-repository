from dataclasses import replace
from datetime import datetime, timedelta

from .. import model
from .core import RepositoryContainer, SimpleRepository


class NewReleasesRemover(RepositoryContainer):
    """
    A component used to remove newly released projects from the source repository.
    This component can be used only if the source repository exposes the upload
    date according to PEP-700: https://peps.python.org/pep-0700/.
    """
    def __init__(
        self,
        source: SimpleRepository,
        quarantine_time: timedelta = timedelta(days=2),
        whitelist: tuple[str, ...] = tuple(),
    ) -> None:
        self._quarantine_time = quarantine_time
        self._whitelist = whitelist
        super().__init__(source)

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
        filtered_files = tuple(
            file for file in project_page.files
            if not file.upload_time or
            (now - file.upload_time).total_seconds() >= self._quarantine_time.total_seconds()
        )
        return replace(project_page, files=filtered_files)
