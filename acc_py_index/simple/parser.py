import json
from urllib.parse import urljoin

import packaging.utils

from .. import html_parser
from .model import File, Meta, ProjectDetail, ProjectList, ProjectListElement


def _url_absolutizer(url: str, url_base: str) -> str:
    """Converts a relative url into an absolute one"""
    if not url.startswith("http") and not url.startswith("https"):
        return urljoin(url_base, url)
    return url


def parse_json_project_list(page: str) -> ProjectList:
    project_dict = json.loads(page)
    projects = {
        ProjectListElement(
            name=project.get("name"),
        ) for project in project_dict["projects"]
    }
    return ProjectList(
        meta=Meta(
            api_version=project_dict["meta"]["api-version"],
        ),
        projects=projects,
    )


def parse_html_project_list(page: str) -> ProjectList:
    parser = html_parser.SimpleHTMLParser()
    if not page.lower().lstrip().startswith("<!DOCTYPE html>"):
        # Temporary fix: https://github.com/pypa/pip/issues/10825
        page = "<!DOCTYPE html>\n" + page
    parser.feed(page)

    projects = {
        ProjectListElement(
            name=packaging.utils.canonicalize_name(element.content),
        )
        for element in parser.elements if element.tag == "a" and element.content is not None
    }

    return ProjectList(
        meta=Meta(
            api_version="1.0",
        ),
        projects=projects,
    )


def parse_json_project_page(source_url: str, body: str) -> ProjectDetail:
    page_dict = json.loads(body)
    return ProjectDetail(
        name=page_dict["name"],
        meta=Meta(
            api_version=page_dict["meta"]["api-version"],
        ),
        files=[
            File(
                filename=file.get("filename"),
                url=_url_absolutizer(file.get("url"), source_url),
                hashes=file.get("hashes"),
                requires_python=file.get("requires-python"),
                dist_info_metadata=file.get("dist-info-metadata"),
                gpg_sig=file.get("gpg-sig"),
                yanked=(file.get("yanked") if file.get("yanked") is not False else None),
            )
            for file in page_dict["files"]
        ],
    )


def parse_html_project_page(source_url: str, page: str, project_name: str) -> ProjectDetail:
    parser = html_parser.SimpleHTMLParser()
    if not page.lower().lstrip().startswith("<!DOCTYPE html>"):
        # Temporary fix: https://github.com/pypa/pip/issues/10825
        page = "<!DOCTYPE html>\n" + page
    parser.feed(page)

    files = []
    a_tags = (e for e in parser.elements if e.tag == "a")
    for a_tag in a_tags:
        hash = {}
        if (url := a_tag.attrs.get("href")) and (a_tag.content is not None):
            url_tokens = url.split('#')
            abs_url = _url_absolutizer(url_tokens[0], source_url)
            if len(url_tokens) > 1:
                hash_string = url_tokens[1].split('=')
                hash[hash_string[0]] = hash_string[1]

            file = File(
                filename=a_tag.content,
                url=abs_url,
                hashes=hash,
            )
        if requires_python := a_tag.attrs.get("data-requires-python"):
            file.requires_python = requires_python
        if dist_info_metadata := a_tag.attrs.get("data-dist-info-metadata"):
            file.dist_info_metadata = dist_info_metadata
        if yanked := a_tag.attrs.get("data-yanked"):
            file.yanked = yanked

        files.append(file)

    return ProjectDetail(
        name=project_name,
        meta=Meta(
            api_version="1.0",
        ),
        files=files,
    )
