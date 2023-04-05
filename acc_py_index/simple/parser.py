import json
from urllib.parse import urldefrag

from .. import html_parser
from .model import File, Meta, ProjectDetail, ProjectList, ProjectListElement


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

    a_tags = (
        element for element in parser.elements
        if element.tag == "a"
    )

    projects = {
        ProjectListElement(
            name=element.content,
        )
        for element in a_tags
        if element.content is not None
    }

    return ProjectList(
        meta=Meta(
            api_version="1.0",
        ),
        projects=projects,
    )


def parse_json_project_page(body: str) -> ProjectDetail:
    page_dict = json.loads(body)
    return ProjectDetail(
        name=page_dict["name"],
        meta=Meta(
            api_version=page_dict["meta"]["api-version"],
        ),
        files=[
            File(
                filename=file["filename"],
                url=file["url"],
                hashes=file["hashes"],
                requires_python=file.get("requires-python"),
                dist_info_metadata=file.get("dist-info-metadata"),
                gpg_sig=(file.get("gpg-sig") if file.get("gpg-sig") is not False else None),
                yanked=(file.get("yanked") if file.get("yanked") is not False else None),
            )
            for file in page_dict["files"]
        ],
    )


def parse_html_project_page(page: str, project_name: str) -> ProjectDetail:
    parser = html_parser.SimpleHTMLParser()
    if not page.lower().lstrip().startswith("<!DOCTYPE html>"):
        # Temporary fix: https://github.com/pypa/pip/issues/10825
        page = "<!DOCTYPE html>\n" + page
    parser.feed(page)

    files = []
    a_tags = (
        e for e in parser.elements if e.tag == "a"
    )

    for a_tag in a_tags:
        if (a_tag.content is None) or (a_tag.attrs.get("href") is None):
            continue

        hashes = {}
        url, anchor = urldefrag(a_tag.attrs["href"])

        if anchor:
            hash_val = str(anchor).split('=')
            hashes[hash_val[0]] = hash_val[1]

        file = File(
            filename=a_tag.content,
            url=str(url),
            hashes=hashes,
            requires_python=a_tag.attrs.get("data-requires-python"),
            dist_info_metadata=a_tag.attrs.get("data-dist-info-metadata"),
            yanked=a_tag.attrs.get("data-yanked"),
            gpg_sig=a_tag.attrs.get("data-gpg-sig"),
        )

        files.append(file)

    return ProjectDetail(
        name=project_name,
        meta=Meta(
            api_version="1.0",
        ),
        files=files,
    )
