# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from html import escape
import json
import typing
from typing import Union

import packaging.utils
import packaging.version

from .content_negotiation import Format
from .model import File, ProjectDetail, ProjectList


class Serializer(typing.Protocol):
    def serialize_project_page(self, page: ProjectDetail) -> str:
        ...

    def serialize_project_list(self, page: ProjectList) -> str:
        ...


class SerializerJsonV1(Serializer):
    def serialize_project_page(self, page: ProjectDetail) -> str:
        project_page_dict = {
            "meta": {
                "api-version": page.meta.api_version,
            },
            "name": page.name,
            "files": [
                self.standardize_file(
                    file=file,
                    version=packaging.version.Version(page.meta.api_version),
                )
                for file in page.files
            ],
        }
        if page.versions is not None:
            project_page_dict["versions"] = list(page.versions)
        return json.dumps(project_page_dict)

    def serialize_project_list(self, page: ProjectList) -> str:
        list_dict = {
           "meta": {"api-version": page.meta.api_version},
           "projects": [
                {"name": elem.name} for elem in page.projects
           ],
        }
        return json.dumps(list_dict)

    def standardize_file(
        self,
        file: File,
        version: packaging.version.Version,
    ) -> dict[str, typing.Any]:
        file_dict: dict[str, typing.Any] = {
            "filename": file.filename,
            "url": file.url,
            "hashes": file.hashes,
        }
        if file.requires_python is not None:
            file_dict["requires-python"] = file.requires_python
        # From PEP-714: The PEP 658 metadata, when used in the PEP 691
        # JSON representation of the Simple API, MUST be emitted using
        # the key core-metadata, with the supported values remaining the same.
        if file.dist_info_metadata is not None:
            file_dict["core-metadata"] = file.dist_info_metadata
        if file.gpg_sig is not None:
            file_dict["gpg-sig"] = file.gpg_sig
        if file.yanked is not None:
            file_dict["yanked"] = file.yanked
        if version >= packaging.version.Version("1.1"):
            file_dict["size"] = file.size
            if file.upload_time is not None:
                file_dict["upload-time"] = file.upload_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        return file_dict


class SerializerHtmlV1(Serializer):
    SIMPLE_PROJECT_HEADER = """<!DOCTYPE html>
    <html>
    <head>
        <meta name="pypi:repository-version" content="{api_version}">
        <title>Links for {project_name}</title>
    </head>
    <body>
    <h1>Links for {project_name}</h1>
"""
    SIMPLE_PROJECT_LINK = '<a {attributes}>{file_name}</a><br/>\n'
    SIMPLE_PROJECT_FOOTER = "</body>\n</html>"
    SIMPLE_INDEX_HEADER = """<!DOCTYPE html>
    <html>
    <head>
        <meta name="pypi:repository-version" content="{api_version}">
        <title>Simple index</title>
    </head>
    <body>
"""
    SIMPLE_INDEX_PROJECT_LINK = '<a href="{href}">{project}</a><br/>\n'
    SIMPLE_INDEX_FOOTER = "</body>\n</html>"

    def serialize_project_page(self, page: ProjectDetail) -> str:
        project_page_html = [
            self.SIMPLE_PROJECT_HEADER.format(
                api_version=page.meta.api_version,
                project_name=page.name,
            ),
        ]

        for file in page.files:
            project_page_html.append(self._serialize_file(file))

        project_page_html.append(self.SIMPLE_PROJECT_FOOTER)
        return "".join(project_page_html)

    def serialize_project_list(self, page: ProjectList) -> str:
        project_list_html = [
            self.SIMPLE_INDEX_HEADER.format(
                api_version=page.meta.api_version,
            ),
        ]
        for project_name in page.projects:
            project_list_html.append(
                self.SIMPLE_INDEX_PROJECT_LINK.format(
                    project=project_name.name,
                    # Using relative paths for project page urls.
                    href=packaging.utils.canonicalize_name(project_name.name) + "/",
                ),
            )
        project_list_html.append(self.SIMPLE_INDEX_FOOTER)
        return "".join(project_list_html)

    def _serialize_file(self, file: File) -> str:
        url = file.url
        attributes = []
        if file.hashes:
            hash_fun = "sha256" if "sha256" in file.hashes else next(iter(file.hashes))
            hash_value = file.hashes[hash_fun]
            fragment = f"{hash_fun}={hash_value}"
            url = f"{url}#{fragment}"

        attributes.append(f'href="{url}"')

        if file.requires_python:
            # From PEP 503: In the attribute value, < and > have to be HTML
            # encoded as &lt; and &gt;, respectively.
            attributes.append(f'data-requires-python="{escape(file.requires_python)}"')

        # From PEP 658: The repository SHOULD provide the hash of the Core Metadata file as the
        # data-dist-info-metadata attribute’s value using the syntax <hashname>=<hashvalue>,
        # where <hashname> is the lower cased name of the hash function used, and <hashvalue>
        # is the hex encoded digest. The repository MAY use true as the attribute’s value
        # if a hash is unavailable.

        # From PEP 714: The PEP 658 metadata, when used in the HTML representation of the Simple
        # API, MUST be emitted using the attribute name data-core-metadata, with the supported
        # values remaining the same.
        if file.dist_info_metadata:
            if file.dist_info_metadata is True:
                attributes.append('data-core-metadata="true"')
            else:
                hash_fun = (
                    "sha256" if "sha256" in file.dist_info_metadata
                    else next(iter(file.dist_info_metadata))
                )
                hash_value = file.dist_info_metadata[hash_fun]
                attributes.append(f'data-core-metadata="{hash_fun}={hash_value}"')

        # From PEP 592: The value of the data-yanked attribute, if present, is an arbitrary
        # string that represents the reason for why the file has been yanked.
        # According to PEP 691, if the reason is not specified, the value of the yanked key
        # is set to True and never to an empty string.
        if file.yanked:
            if file.yanked is True:
                attributes.append('data-yanked=""')
            else:
                attributes.append(f'data-yanked="{file.yanked}"')

        # From PEP 503: A repository MAY include a data-gpg-sig attribute on a file link with
        # a value of either true or false to indicate whether or not there is a GPG signature.
        if file.gpg_sig:
            attributes.append('data-gpg-sig="true"')
        elif file.gpg_sig is False:
            attributes.append('data-gpg-sig="false"')

        attributes_string = " ".join(attributes)

        return self.SIMPLE_PROJECT_LINK.format(
            file_name=file.filename,
            attributes=attributes_string,
        )


serializers: dict[Format, Serializer] = {
    Format.JSON_V1: SerializerJsonV1(),
    Format.HTML_V1: SerializerHtmlV1(),
    Format.HTML_LEGACY: SerializerHtmlV1(),
}


def serialize(page: Union[ProjectDetail, ProjectList], format: Format) -> str:
    serializer = serializers.get(format)
    if serializer is None:
        raise ValueError("Unsupported format")

    if isinstance(page, ProjectList):
        return serializer.serialize_project_list(page)
    elif isinstance(page, ProjectDetail):
        return serializer.serialize_project_page(page)
    else:
        raise ValueError("Unsupported page type")
