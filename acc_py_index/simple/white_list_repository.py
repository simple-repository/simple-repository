import pathlib

import packaging.utils

from .. import errors, utils
from .model import Meta, ProjectDetail, ProjectList, ProjectListElement, Resource
from .repositories import SimpleRepository


class WhitelistRepository(SimpleRepository):
    """Exposes only the whitelisted projects of the source repository.
    Projects available from the source but not added to the
    whitelist file are made not available available from this repository.
    """
    def __init__(
        self,
        source: SimpleRepository,
        special_case_file: pathlib.Path,
    ) -> None:
        self.source = source
        self.special_case_file = special_case_file

    async def get_project_page(self, project_name: str) -> ProjectDetail:
        """Returns the project page from the source if the project_name
        is whitelisted. Raises PackageNotFoundError otherwise. Raises
        NotNormalizedProjectName if project_name is not normalized.
        """

        if project_name != packaging.utils.canonicalize_name(project_name):
            raise errors.NotNormalizedProjectName()

        special_cases = utils.load_cached_json_config(self.special_case_file)

        if project_name not in special_cases:
            raise errors.PackageNotFoundError(project_name)
        else:
            return await self.source.get_project_page(project_name)

    async def get_project_list(self) -> ProjectList:
        return ProjectList(
            meta=Meta("1.0"),
            projects={
                ProjectListElement(name) for name in
                utils.load_cached_json_config(self.special_case_file).keys()
            },
        )

    async def get_resource(self, project_name: str, resource_name: str) -> Resource:
        if project_name in utils.load_cached_json_config(self.special_case_file):
            return await self.source.get_resource(project_name, resource_name)
        raise errors.ResourceUnavailable(resource_name)
