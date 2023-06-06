from enum import Enum
from html import escape
import json
import typing
from typing import Union

import packaging.utils

from .model import File, ProjectDetail, ProjectList


class Format(Enum):
    JSON_V1: str = "application/vnd.pypi.simple.v1+json"
    HTML_V1: str = "application/vnd.pypi.simple.v1+html"
    HTML_LEGACY: str = "text/html"


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
                self.standardize_file(file)
                for file in page.files
            ],

        }
        return json.dumps(project_page_dict)

    def serialize_project_list(self, page: ProjectList) -> str:
        list_dict = {
           "meta": {"api-version": page.meta.api_version},
           "projects": [
                {"name": elem.name} for elem in page.projects
           ],
        }
        return json.dumps(list_dict)

    def standardize_file(self, file: File) -> dict[str, typing.Any]:
        file_dict: dict[str, typing.Any] = {
            "filename": file.filename,
            "url": file.url,
            "hashes": file.hashes,
        }
        if file.requires_python is not None:
            file_dict["requires-python"] = file.requires_python
        if file.dist_info_metadata is not None:
            file_dict["dist-info-metadata"] = file.dist_info_metadata
        if file.gpg_sig is not None:
            file_dict["gpg-sig"] = file.gpg_sig
        if file.yanked is not None:
            file_dict["yanked"] = file.yanked
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
        if file.dist_info_metadata:
            if file.dist_info_metadata is True:
                attributes.append('data-dist-info-metadata="true"')
            else:
                hash_fun = (
                    "sha256" if "sha256" in file.dist_info_metadata
                    else next(iter(file.dist_info_metadata))
                )
                hash_value = file.dist_info_metadata[hash_fun]
                attributes.append(f'data-dist-info-metadata="{hash_fun}={hash_value}"')

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
