from acc_py_index.simple import serializer
from acc_py_index.simple.model import File, Meta, ProjectDetail, ProjectList, ProjectListElement


def test_serialize_file_html() -> None:
    file = File(
        filename="test.html",
        url="https://example.com/test.html",
        hashes={"sha256": "abc123"},
        requires_python=">=3.6",
        dist_info_metadata="metadata.json",
        yanked="Broken",
    )
    expected = (
        '<a href="https://example.com/test.html#sha256:abc123" data-requires-python=">=3.6" '
        'data-dist-info-metadata="metadata.json" data-yanked="Broken">test.html</a><br/>\n'
    )
    assert serializer._serialize_file_html(file) == expected


def test_serialize_project_page_html() -> None:
    project_page = ProjectDetail(
        meta=Meta(api_version="1.0"),
        name="test-project",
        files=[
            File(filename="test.html", url="https://example.com/test.html", hashes={}),
            File(filename="test.txt", url="https://example.com/test.txt", hashes={}),
        ],
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
<a href="https://example.com/test.txt">test.txt</a><br/>
</body>
</html>"""
    assert serializer._serialize_project_page_html(project_page) == expected


def test_serialize_project_list_html() -> None:
    project_list = ProjectList(
        meta=Meta(api_version="1.0"),
        projects={
            ProjectListElement(name="test-project-1"),
            ProjectListElement(name="test-project-2"),
        },
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

    serialized_page = serializer._serialize_project_list_html(project_list)
    assert serialized_page.startswith(expected_header)
    assert serialized_page.endswith(expected_footer)
    a_tags = serialized_page.removeprefix(expected_header).removesuffix(expected_footer)
    assert '<a href="/simple/test-project-1/">test-project-1</a><br/>' in a_tags
    assert '<a href="/simple/test-project-2/">test-project-2</a><br/>' in a_tags
