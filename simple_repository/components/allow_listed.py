# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import pathlib

import packaging.utils

from .. import errors, model, utils
from .core import SimpleRepository


class AllowListedRepository(SimpleRepository):
    """Exposes only the whitelisted projects of the source repository.
    Projects available from the source but not added to the
    whitelist file are not made available from this repository.
    """
    def __init__(
        self,
        source: SimpleRepository,
        special_case_file: pathlib.Path,
    ) -> None:
        self.source = source
        self._special_cases: dict[str, str] = self._load_config_json(special_case_file)
        self.special_case_file = special_case_file

    async def get_project_page(
        self,
        project_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectDetail:
        """Returns the project page from the source if the project_name
        is whitelisted.
        """
        if project_name not in self._special_cases:
            raise errors.PackageNotFoundError(project_name)
        else:
            return await self.source.get_project_page(
                project_name,
                request_context=request_context,
            )

    async def get_project_list(
        self,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.ProjectList:
        return model.ProjectList(
            meta=model.Meta("1.0"),
            projects=frozenset(
                model.ProjectListElement(name) for name in
                self._special_cases.keys()
            ),
        )

    async def get_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        request_context: model.RequestContext = model.RequestContext.DEFAULT,
    ) -> model.Resource:
        if project_name in self._special_cases:
            return await self.source.get_resource(
                project_name,
                resource_name,
                request_context=request_context,
            )
        raise errors.ResourceUnavailable(resource_name)

    def _load_config_json(self, json_file: pathlib.Path) -> dict[str, str]:
        json_config = utils.load_config_json(json_file)

        config_dict: dict[str, str] = {}
        for key, value in json_config.items():
            if (
                not isinstance(key, str) or
                not isinstance(value, str)
            ):
                raise errors.InvalidConfigurationError(
                    f'Invalid special case configuration file. {json_file} '
                    'must contain a dictionary mapping a project name to a tuple'
                    ' containing a glob pattern and a yank reason.',
                )
            config_dict[packaging.utils.canonicalize_name(key)] = value

        return config_dict
