# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from enum import Enum

from . import errors


class Format(Enum):
    JSON_V1: str = "application/vnd.pypi.simple.v1+json"
    HTML_V1: str = "application/vnd.pypi.simple.v1+html"
    HTML_LEGACY: str = "text/html"


def select_response_format(content_type: str) -> Format:
    if not content_type:
        return Format.HTML_LEGACY

    content_type_tokens = content_type.split(",")
    requested_formats = []

    for token in content_type_tokens:
        token_pieces = token.replace(" ", "").split(";")
        q = 1.0
        if len(token_pieces) == 2:
            q = float(token_pieces[1].removeprefix("q="))
        requested_formats.append(
            (token_pieces[0], q),
        )
    # Requested content-types sorted by q value
    sorted_formats = sorted(
        requested_formats, key=lambda f: f[1], reverse=True,
    )
    for form, _ in sorted_formats:
        if form == "*/*":
            return Format.HTML_LEGACY
        try:
            return Format(form)
        except ValueError:
            pass

    raise errors.UnsupportedSerialization(content_type)
