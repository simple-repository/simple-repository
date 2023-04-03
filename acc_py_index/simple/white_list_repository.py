import json
import pathlib
import sys
import typing

import cachetools
import packaging.utils

from .. import errors
from .model import Meta, ProjectDetail, ProjectList, ProjectListElement
from .repositories import SimpleRepository


@cachetools.cached(cache=cachetools.TTLCache(maxsize=sys.maxsize, ttl=30))
def get_special_cases(special_cases_file: pathlib.Path) -> typing.Iterable[str]:
    with special_cases_file.open() as file:
        special_cases: dict[str, str] = json.load(file)
        return special_cases.keys()


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
        if project_name != packaging.utils.canonicalize_name(project_name):
            raise errors.NotNormalizedProjectName()

        special_cases = get_special_cases(self.special_case_file)

        if project_name not in special_cases:
            raise errors.PackageNotFoundError(project_name)
        else:
            return await self.source.get_project_page(project_name)

    async def get_project_list(self) -> ProjectList:
        return ProjectList(
            meta=Meta("1.0"),
            projects={
                ProjectListElement(name) for name in
                get_special_cases(self.special_case_file)
            },
        )
