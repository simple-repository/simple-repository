# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from datetime import datetime
import json
from typing import Optional, Union

import pytest

from ..model import File, Meta, ProjectDetail, ProjectList, ProjectListElement
from ..serializer import SerializerHtmlV1, SerializerJsonV1


def test_serialize_file_html() -> None:
    serializer = SerializerHtmlV1()

    file = File(
        filename="test.html",
        url="https://example.com/test.html",
        hashes={"test": "123", "sha256": "abc123"},
        requires_python=">=3.6",
    )
    expected = (
        '<a href="https://example.com/test.html#sha256=abc123" data-requires-python="&gt;=3.6"'
        '>test.html</a><br/>\n'
    )
    assert serializer._serialize_file(file) == expected

    file = File(
        filename="test.html",
        url="https://example.com/test.html",
        hashes={},
    )
    expected = (
        '<a href="https://example.com/test.html"'
        '>test.html</a><br/>\n'
    )
    assert serializer._serialize_file(file) == expected


@pytest.mark.parametrize(
    "yank_attr, yank_value",
    [
        (' data-yanked=""', True),
        (' data-yanked="reason"', "reason"),
        ('', None),
        ('', False),
    ],
)
def test_serialize_file_html_yank(
    yank_attr: str,
    yank_value: Optional[Union[bool, str]],
) -> None:
    serializer = SerializerHtmlV1(

    )
    file = File(
        filename="test.html",
        url="https://example.com/test.html",
        hashes={},
        yanked=yank_value,
    )
    expected = (
        '<a href="https://example.com/test.html"'
        f'{yank_attr}'
        '>test.html</a><br/>\n'
    )
    assert serializer._serialize_file(file) == expected


@pytest.mark.parametrize(
    "metadata_attr, metadata_value",
    [
        (' data-core-metadata="true"', True),
        (' data-core-metadata="sha=..."', {"sha": "..."}),
        ('', None),
        ('', False),
    ],
)
def test_serialize_file_html_metadata(
    metadata_attr: str,
    metadata_value: Optional[Union[bool, dict[str, str]]],
) -> None:
    serializer = SerializerHtmlV1()

    file = File(
        filename="test.html",
        url="https://example.com/test.html",
        hashes={},
        dist_info_metadata=metadata_value,
    )
    expected = (
        '<a href="https://example.com/test.html"'
        f'{metadata_attr}'
        '>test.html</a><br/>\n'
    )
    assert serializer._serialize_file(file) == expected


@pytest.mark.parametrize(
    "gpg_attr, gpg_value",
    [
        (' data-gpg-sig="true"', True),
        (' data-gpg-sig="false"', False),
        ('', None),
    ],
)
def test_serialize_file_html_gpg(gpg_attr: str, gpg_value: Optional[bool]) -> None:
    serializer = SerializerHtmlV1()

    file = File(
        filename="test.html",
        url="https://example.com/test.html",
        hashes={},
        gpg_sig=gpg_value,
    )
    expected = (
        '<a href="https://example.com/test.html"'
        f'{gpg_attr}'
        '>test.html</a><br/>\n'
    )
    assert serializer._serialize_file(file) == expected


def test_serialize_project_page_html() -> None:
    project_page = ProjectDetail(
        meta=Meta(api_version="1.0"),
        name="test-project",
        files=(
            File(filename="test.html", url="https://example.com/test.html", hashes={}),
            File(filename="test.txt", url="test.txt", hashes={}),
        ),
    )
    expected = """<!DOCTYPE html>
    <html>
    <head>
        <meta name="pypi:repository-version" content="1.0">
        <title>Links for test-project</title>
    </head>
    <body>
    <h1>Links for test-project</h1>
<a href="https://example.com/test.html">test.html</a><br/>
<a href="test.txt">test.txt</a><br/>
</body>
</html>"""
    serializer = SerializerHtmlV1()
    assert serializer.serialize_project_page(project_page) == expected


def test_serialize_project_list_html() -> None:
    project_list = ProjectList(
        meta=Meta(api_version="1.0"),
        projects=frozenset([
            ProjectListElement(name="test-project-1"),
            ProjectListElement(name="test-project-2"),
        ]),
    )
    expected_header = """<!DOCTYPE html>
    <html>
    <head>
        <meta name="pypi:repository-version" content="1.0">
        <title>Simple index</title>
    </head>
    <body>
"""
    expected_footer = """</body>
</html>"""

    serializer = SerializerHtmlV1()
    serialized_page = serializer.serialize_project_list(project_list)
    assert serialized_page.startswith(expected_header)
    assert serialized_page.endswith(expected_footer)
    a_tags = serialized_page.removeprefix(expected_header).removesuffix(expected_footer)
    assert '<a href="test-project-1/">test-project-1</a><br/>' in a_tags
    assert '<a href="test-project-2/">test-project-2</a><br/>' in a_tags


def test_serialize_project_page_json() -> None:
    page = ProjectDetail(
        Meta("1.0"),
        "project",
        files=(
            File(
                filename="test1.whl",
                url="test1.whl",
                hashes={},
            ),
            File(
                filename="test2.whl",
                url="test2.whl",
                hashes={"hash": "test_hash"},
                requires_python=">4.0",
                dist_info_metadata=True,
                yanked="yanked",
                gpg_sig=True,
            ),
            File(
                filename="test3.whl",
                url="test3.whl",
                hashes={},
                dist_info_metadata={"sha": "..."},
                yanked=True,
            ),
        ),
    )
    serializer = SerializerJsonV1()
    res = serializer.serialize_project_page(page)

    assert json.loads(res) == json.loads('''
        {
            "meta": {
                "api-version": "1.0"
            },
            "name": "project",
            "files": [
                {
                    "filename": "test1.whl",
                    "url": "test1.whl",
                    "hashes": {}
                },
                {
                    "filename": "test2.whl",
                    "url": "test2.whl",
                    "hashes": {"hash": "test_hash"},
                    "requires-python": ">4.0",
                    "core-metadata": true,
                    "yanked": "yanked",
                    "gpg-sig": true
                },
                {
                    "filename": "test3.whl",
                    "url": "test3.whl",
                    "hashes": {},
                    "core-metadata": {"sha": "..."},
                    "yanked": true
                }
            ]
        }
    ''')


@pytest.mark.parametrize(
    "version, serialization", [
        (
            "1.0",
            '''[{
                "filename": "test1-1.0.whl",
                "url": "test1.whl",
                "hashes": {}
            }]''',
        ),
        (
            "1.1",
            '''[{
                "filename": "test1-1.0.whl",
                "url": "test1.whl",
                "hashes": {},
                "size": 1,
                "upload-time": "2000-01-04T00:00:00Z"
            }]''',
        ),
    ],
)
def test_serialize_project_page_json__v1_1_attrs(
    version: str,
    serialization: str,
) -> None:
    page = ProjectDetail(
        Meta(version),
        "project",
        files=(
            File(
                filename="test1-1.0.whl",
                url="test1.whl",
                hashes={},
                size=1,
                upload_time=datetime(2000, 1, 4, 0, 0, 0),
            ),
        ),
    )
    serializer = SerializerJsonV1()
    res = serializer.serialize_project_page(page)
    assert json.loads(res)["files"] == json.loads(serialization)


def test_serialize_project_list_json() -> None:
    page = ProjectList(
        Meta("1.0"),
        projects=frozenset([
            ProjectListElement("a"),
        ]),
    )
    serializer = SerializerJsonV1()
    res = serializer.serialize_project_list(page)

    assert res == json.dumps(
        json.loads('''{
        "meta": {
            "api-version": "1.0"
        },
        "projects": [
            {"name": "a"}
        ]
    }'''),
    )
