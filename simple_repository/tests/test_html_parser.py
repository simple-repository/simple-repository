# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

"""Test the custom html parser that's used for parsing (remote) Simple index html pages

Currently, there are no tests written for parsing invalid HTML.
This is because it (html.parser.HTMLParser) does not throw errors, but gives strange results instead
"""

from __future__ import annotations

from ..html_parser import HTMLElement, SimpleHTMLParser


def test_parser() -> None:
    parser = SimpleHTMLParser()
    data = """<!DOCTYPE html>
<html>
  <head>
    <meta name="pypi:repository-version" content="1.0"/>
    <title>Title</title>
  </head>
  <body>
    <h1>Header</h1>
    <a href="../../hammer/hammer-1.0.tar.gz">hammer-1.0.tar.gz</a><br/>
    <a href="../../shovel/shovel-1.0.whl" extra-attr>shovel-1.0.whl</a><br/>
    <a href="../../drill/drill-1.0.whl" extra-attr="true">drill-1.0.whl</a><br/>
  </body>
</html>
"""
    parser.feed(data)
    assert parser.declaration == "DOCTYPE html"
    emtpy_attr = HTMLElement(
        "a",
        {"href": "../../shovel/shovel-1.0.whl", "extra-attr": None},
        "shovel-1.0.whl",
    )
    assert parser.elements == [
        HTMLElement("html", {}),
        HTMLElement("head", {}),
        HTMLElement("meta", {"name": "pypi:repository-version", "content": "1.0"}),
        HTMLElement("title", {}, "Title"),
        HTMLElement("body", {}),
        HTMLElement("h1", {}, "Header"),
        HTMLElement(
            "a",
            {"href": "../../hammer/hammer-1.0.tar.gz"},
            "hammer-1.0.tar.gz",
        ),
        HTMLElement("br", {}),
        emtpy_attr,
        HTMLElement("br", {}),
        HTMLElement(
            "a",
            {"href": "../../drill/drill-1.0.whl", "extra-attr": "true"},
            "drill-1.0.whl",
        ),
        HTMLElement("br", {}),
    ]
    assert (
        str(emtpy_attr)
        == '<a href="../../shovel/shovel-1.0.whl" extra-attr="">shovel-1.0.whl</a>'
    )
