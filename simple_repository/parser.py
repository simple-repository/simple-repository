# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

from datetime import datetime
import html
import json
import typing
import urllib.parse

from . import html_parser, model


def parse_json_project_list(page: str) -> model.ProjectList:
    project_dict = json.loads(page)
    projects = frozenset(
        model.ProjectListElement(
            name=project.get("name"),
            private_metadata=_gather_private_attribs(project),
        )
        for project in project_dict["projects"]
    )
    return model.ProjectList(
        meta=model.Meta(
            api_version=project_dict["meta"]["api-version"],
            private_metadata=_gather_private_attribs(project_dict["meta"]),
        ),
        projects=projects,
        private_metadata=_gather_private_attribs(project_dict),
    )


def parse_html_project_list(page: str) -> model.ProjectList:
    parser = html_parser.SimpleHTMLParser()
    if not page.lower().lstrip().startswith("<!DOCTYPE html>"):
        # Temporary fix: https://github.com/pypa/pip/issues/10825
        page = "<!DOCTYPE html>\n" + page
    parser.feed(page)

    a_tags = (element for element in parser.elements if element.tag == "a")

    projects = frozenset(
        model.ProjectListElement(
            name=element.content,
        )
        for element in a_tags
        if element.content is not None
    )

    return model.ProjectList(
        meta=model.Meta(
            api_version="1.0",
        ),
        projects=projects,
    )


def parse_json_project_page(body: str) -> model.ProjectDetail:
    page_dict = json.loads(body)

    files = []
    for file in page_dict["files"]:
        date_string = file.get("upload-time")
        if date_string:
            # PEP-700: upload-time MUST contain a valid ISO 8601 date/time string, in the format
            # yyyy-mm-ddThh:mm:ss.ffffffZ, which represents the time the file was uploaded to
            # the index. The fractional seconds part of the timestamp is optional.
            try:
                upload_time = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                upload_time = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            upload_time = None
        files.append(
            model.File(
                filename=file["filename"],
                # Temporary fix: Escape the URLs coming from the source
                # since Nexus is not escaping them correctly. The "safe" parameter
                # allows the escape function to be applied to the entire URL
                # and avoids escaping the special characters ":" and "/".
                url=urllib.parse.quote(file["url"], safe=":/"),
                hashes=file["hashes"],
                requires_python=file.get("requires-python"),
                # PEP-714: Clients consuming the JSON representation of the Simple API MUST
                #          read the PEP 658 metadata from the key core-metadata if it is present.
                dist_info_metadata=file.get("core-metadata"),
                gpg_sig=file.get("gpg-sig"),
                yanked=file.get("yanked"),
                size=file.get("size"),
                upload_time=upload_time,
                private_metadata=_gather_private_attribs(file),
            ),
        )
    versions = page_dict.get("versions", None)
    if versions is not None:
        versions = frozenset(versions)

    return model.ProjectDetail(
        name=page_dict["name"],
        meta=model.Meta(
            api_version=page_dict["meta"]["api-version"],
            private_metadata=_gather_private_attribs(page_dict["meta"]),
        ),
        files=tuple(files),
        versions=versions,
        private_metadata=_gather_private_attribs(page_dict),
    )


def parse_html_project_page(page: str, project_name: str) -> model.ProjectDetail:
    parser = html_parser.SimpleHTMLParser()
    if not page.lower().lstrip().startswith("<!DOCTYPE html>"):
        # Temporary fix: https://github.com/pypa/pip/issues/10825
        page = "<!DOCTYPE html>\n" + page
    parser.feed(page)

    files = []
    a_tags = (e for e in parser.elements if e.tag == "a")

    for a_tag in a_tags:
        if (a_tag.content is None) or (a_tag.attrs.get("href") is None):
            continue

        hashes = {}
        url, fragment = urllib.parse.urldefrag(a_tag.attrs["href"])

        if fragment:
            # PEP-503: The URL SHOULD include a hash in the form of a URL fragment with
            #          the following syntax: #<hashname>=<hashvalue>
            if "=" in fragment:
                hash_name, hash_value = str(fragment).split("=", 1)
                hashes[hash_name] = hash_value

        yanked: typing.Union[bool, str, None] = None
        if "data-yanked" in a_tag.attrs:
            reason = a_tag.attrs.get("data-yanked")
            if reason:
                # Note that the reason can equally be the string "false" and it is
                # still considered yanked.
                yanked = reason
            else:
                # The data-yanked value is not set or is an empty string, replace it with True.
                yanked = True

        dist_info_metadata: typing.Union[bool, typing.Dict[str, str], None] = None
        # PEP-714: Clients consuming any of the HTML representations of the Simple API MUST
        #          read the PEP 658 metadata from the key data-core-metadata if it is present.
        if "data-core-metadata" in a_tag.attrs:
            # PEP-658: The repository SHOULD provide the hash of the Core Metadata file
            #          as the data-dist-info-metadata attribute’s value using
            #          the syntax <hashname>=<hashvalue>
            metadata_val = a_tag.attrs.get("data-core-metadata")
            if metadata_val is None:
                # data-core-metadata is set but doesn't have a value.
                dist_info_metadata = True
            else:
                metadata_attr_tokens = metadata_val.split("=", 1)
                if len(metadata_attr_tokens) == 2:
                    # the value of data-core-metadata can be parsed as <hash_fun>=<hash_val>.
                    dist_info_metadata = {
                        metadata_attr_tokens[0]: metadata_attr_tokens[1],
                    }
                else:
                    # the value of data-core-metadata is a placeholder. It doesn't follow
                    # the SHOULD recommendation, but it is still indicating that the
                    # metadata exists.
                    dist_info_metadata = True

        gpg_sig: typing.Optional[bool] = None
        gpg_sig_value = a_tag.attrs.get("data-gpg-sig")
        if gpg_sig_value:
            # PEP-503: A repository MAY include a data-gpg-sig attribute on a file link with
            #          a value of either true or false to indicate whether or not there is a
            #          GPG signature. Repositories that do this SHOULD include it on every link.
            if gpg_sig_value == "true":
                gpg_sig = True
            elif gpg_sig_value == "false":
                gpg_sig = False

        requires_python: typing.Optional[str] = None
        requires_python_attr = a_tag.attrs.get("data-requires-python")
        if requires_python_attr is not None:
            # PEP-503: A repository MAY include a data-requires-python attribute on a file link.
            #          This exposes the Requires-Python metadata field, specified in PEP 345, for
            #          the corresponding release. Where this is present, installer tools SHOULD
            #          ignore the download when installing to a Python version that doesn’t
            #          satisfy the requirement. In the attribute value, < and > have to be HTML
            #          encoded as &lt; and &gt;, respectively.
            requires_python = html.unescape(requires_python_attr)

        file = model.File(
            filename=a_tag.content,
            # Temporary fix: Escape the URLs coming from the source
            # since Nexus is not escaping them correctly. The "safe" parameter
            # allows the escape function to be applied to the entire URL
            # and avoids escaping the special characters ":" and "/".
            url=urllib.parse.quote(str(url), safe=":/"),
            hashes=hashes,
            requires_python=requires_python,
            dist_info_metadata=dist_info_metadata,
            yanked=yanked,
            gpg_sig=gpg_sig,
        )

        files.append(file)

    return model.ProjectDetail(
        name=project_name,
        meta=model.Meta(
            api_version="1.0",
        ),
        files=tuple(files),
    )


def _gather_private_attribs(
    element: typing.Mapping[str, typing.Any],
) -> model.PrivateMetadataMapping:
    return model.PrivateMetadataMapping.from_any_mapping(
        {name: value for name, value in element.items() if name.startswith("_")},
    )
