import json
import pathlib

import packaging.utils
from packaging.utils import canonicalize_name

from .. import errors
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
        self._special_cases: dict[str, str] = self._load_config_json(special_case_file)
        self.special_case_file = special_case_file

    async def get_project_page(self, project_name: str) -> ProjectDetail:
        """Returns the project page from the source if the project_name
        is whitelisted. Raises PackageNotFoundError otherwise. Raises
        NotNormalizedProjectName if project_name is not normalized.
        """

        if project_name != packaging.utils.canonicalize_name(project_name):
            raise errors.NotNormalizedProjectName()

        if project_name not in self._special_cases:
            raise errors.PackageNotFoundError(project_name)
        else:
            return await self.source.get_project_page(project_name)

    async def get_project_list(self) -> ProjectList:
        return ProjectList(
            meta=Meta("1.0"),
            projects={
                ProjectListElement(name) for name in
                self._special_cases.keys()
            },
        )

    async def get_resource(self, project_name: str, resource_name: str) -> Resource:
        if project_name in self._special_cases:
            return await self.source.get_resource(project_name, resource_name)
        raise errors.ResourceUnavailable(resource_name)

    def _load_config_json(self, json_file: pathlib.Path) -> dict[str, str]:
        try:
            json_config = json.loads(json_file.read_text())
        except json.JSONDecodeError as e:
            raise errors.InvalidConfiguration(f"Invalid json file: {str(e)}")
        if not isinstance(json_config, dict):
            raise errors.InvalidConfiguration(
                "The special case configuration file must contain a"
                " dictionary mapping project names to repository URLs.",
            )
        config_dict: dict[str, str] = {}
        for key, value in json_config.items():
            if (
                not isinstance(key, str) or
                not isinstance(value, str)
            ):
                raise errors.InvalidConfiguration(
                    "The special case configuration file must contain a"
                    " dictionary mapping project names to repository URLs.",
                )
            config_dict[canonicalize_name(key)] = value

        return config_dict
