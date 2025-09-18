# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import html.parser
import typing


class HTMLElement:
    __slots__ = ("tag", "attrs", "content")

    def __init__(
        self,
        tag: str,
        attrs: typing.Dict[str, typing.Optional[str]],
        content: typing.Optional[str] = None,
    ) -> None:
        self.tag = tag
        self.attrs = attrs
        self.content = content

    def __str__(self) -> str:
        result = f"<{self.tag}"
        result += "".join(
            f' {key}="{value if value else ""}"' for key, value in self.attrs.items()
        )
        result += f">{self.content}</{self.tag}>" if self.content else "/>"
        return result

    def __repr__(self) -> str:
        return f"{type(self).__name__}(tag={self.tag}, attrs={self.attrs}, content={self.content})"

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, HTMLElement):
            return False
        return (
            self.tag == other.tag
            and self.attrs == other.attrs
            and self.content == other.content
        )


class SimpleHTMLParser(html.parser.HTMLParser):
    """HTML parser for very basic use-cases, can break with more complex HTML

    pip has an even simpler implementation, but that is not able to parse the Project List page
    (https://github.com/pypa/pip/blob/main/src/pip/_internal/index/collector.py#L395-L420_).


    Important:
        Parsing of invalid HTML will result in tag's and data being mixed up, so strange results.
        The only time when this parser seems to error is with decoding issues.
    """

    def __init__(self, *, convert_charrefs: bool = True) -> None:
        super().__init__(convert_charrefs=convert_charrefs)
        self.declaration: typing.Optional[str] = None
        self.elements: typing.List[HTMLElement] = []
        self._current_tag: typing.Optional[str] = None
        self._current_data: typing.Optional[str] = None

    def handle_decl(self, decl: str) -> None:
        self.declaration = decl

    def handle_starttag(
        self,
        tag: str,
        attrs: typing.List[typing.Tuple[str, typing.Optional[str]]],
    ) -> None:
        self.elements.append(HTMLElement(tag, dict(attrs)))
        self._current_tag = tag
        self._current_data = None

    def handle_data(self, data: str) -> None:
        self._current_data = data

    def handle_endtag(self, tag: str) -> None:
        if tag == self._current_tag:
            self.elements[-1].content = self._current_data
