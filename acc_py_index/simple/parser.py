import json
from typing import Optional, Union
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
                gpg_sig=file.get("gpg-sig"),
                yanked=file.get("yanked"),
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
        url, fragment = urldefrag(a_tag.attrs["href"])

        if fragment:
            # PEP-503: The URL SHOULD include a hash in the form of a URL fragment with
            #          the following syntax: #<hashname>=<hashvalue>
            if '=' in fragment:
                hash_name, hash_value = fragment.split('=', 1)
                hashes[hash_name] = hash_value

        yanked: Optional[Union[bool, str]] = None
        if "data-yanked" in a_tag.attrs:
            if reason := a_tag.attrs.get("data-yanked"):
                # Note that the reason can equally be the string "false" and it is
                # still considered yanked.
                yanked = reason
            else:
                # The data-yanked value is not set or is an empty string, replace it with True.
                yanked = True

        dist_info_metadata: Optional[Union[bool, dict[str, str]]] = None
        if "data-dist-info-metadata" in a_tag.attrs:
            # PEP-658: The repository SHOULD provide the hash of the Core Metadata file
            #          as the data-dist-info-metadata attribute’s value using
            #          the syntax <hashname>=<hashvalue>
            metadata_val = a_tag.attrs.get("data-dist-info-metadata")
            if metadata_val is None:
                # data-dist-info-metadata is set but doesn't have a value.
                dist_info_metadata = True
            else:
                metadata_attr_tokens = metadata_val.split("=", 1)
                if len(metadata_attr_tokens) == 2:
                    # the value of data-dist-info-metadata can be parsed as <hash_fun>=<hash_val>.
                    dist_info_metadata = {metadata_attr_tokens[0]: metadata_attr_tokens[1]}
                else:
                    # the value of data-dist-info-metadata is a placeholder. It doesn't follow
                    # the SHOULD recommendation, but it is still indicating that the
                    # metadata exists.
                    dist_info_metadata = True

        gpg_sig: Optional[bool] = None
        if gpg_sig_value := a_tag.attrs.get("data-gpg-sig"):
            # PEP-503: A repository MAY include a data-gpg-sig attribute on a file link with
            #          a value of either true or false to indicate whether or not there is a
            #          GPG signature. Repositories that do this SHOULD include it on every link.
            if gpg_sig_value == "true":
                gpg_sig = True
            elif gpg_sig_value == "false":
                gpg_sig = False

        file = File(
            filename=a_tag.content,
            url=str(url),
            hashes=hashes,
            requires_python=a_tag.attrs.get("data-requires-python"),
            dist_info_metadata=dist_info_metadata,
            yanked=yanked,
            gpg_sig=gpg_sig,
        )

        files.append(file)

    return ProjectDetail(
        name=project_name,
        meta=Meta(
            api_version="1.0",
        ),
        files=files,
    )
