from typing import Union

import packaging.utils

from .model import File, ProjectDetail, ProjectList

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


def _serialize_file_html(file: File) -> str:
    url = file.url
    attributes = []
    if file.hashes:
        hash_fun = next(iter(file.hashes))
        hash_value = file.hashes[hash_fun]
        url += f"#{hash_fun}:{hash_value}"
    attributes.append(f'href="{url}"')

    if file.requires_python:
        attributes.append(f'data-requires-python="{file.requires_python}"')

    if file.dist_info_metadata:
        attributes.append(f'data-dist-info-metadata="{file.dist_info_metadata}"')

    if file.yanked:
        attributes.append(f'data-yanked="{file.yanked}"')

    attributes_string = " ".join(attributes)

    return SIMPLE_PROJECT_LINK.format(
        file_name=file.filename,
        attributes=attributes_string,
    )


def _serialize_project_page_html(project_page: ProjectDetail) -> str:
    project_page_html = [
        SIMPLE_PROJECT_HEADER.format(
            api_version=project_page.meta.api_version,
            project_name=project_page.name,
        ),
    ]

    for file in project_page.files:
        project_page_html.append(_serialize_file_html(file))

    project_page_html.append(SIMPLE_PROJECT_FOOTER)
    return "".join(project_page_html)


def _serialize_project_list_html(project_list: ProjectList) -> str:
    project_list_html = [
        SIMPLE_INDEX_HEADER.format(
            api_version=project_list.meta.api_version,
        ),
    ]
    for project_name in project_list.projects:
        project_list_html.append(
            SIMPLE_INDEX_PROJECT_LINK.format(
                project=project_name.name,
                href=packaging.utils.canonicalize_name(project_name.name) + "/",
            ),
        )
    project_list_html.append(SIMPLE_INDEX_FOOTER)
    return "".join(project_list_html)


def serialize_html(page: Union[ProjectDetail, ProjectList]) -> str:
    """Serialises a ProjectDetail or ProjectList object
    into the html format standardised by PEP503."""

    if isinstance(page, ProjectDetail):
        return _serialize_project_page_html(page)

    if isinstance(page, ProjectList):
        return _serialize_project_list_html(page)
