# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import pytest

from .. import content_negotiation, errors


@pytest.mark.parametrize(
    "content_type, format",
    [
        ("", content_negotiation.Format.HTML_LEGACY),
        (
            "application/vnd.pypi.simple.v1+html;q=0.8,application/vnd.pypi.simple.v1+json;q=0.9",
            content_negotiation.Format.JSON_V1,
        ),
        (
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            content_negotiation.Format.HTML_LEGACY,
        ),
        (
            "application/vnd.pypi.simple.v1+html,application/xhtml+xml;q=0.1",
            content_negotiation.Format.HTML_V1,
        ),
        (
            "application/vnd.pypi.simple.v1+json; q = 0.9, application/vnd.pypi.simple.v1+html; q = 0.8",
            content_negotiation.Format.JSON_V1,
        ),
    ],
)
def test_select_response_format(
    content_type: str,
    format: content_negotiation.Format,
) -> None:
    assert content_negotiation.select_response_format(content_type) == format


@pytest.mark.parametrize(
    "content_type",
    [
        "application/json",
        "application/vnd.pypi.simple.v2+json;q=0.9 , application/vnd.pypi.simple.v2+html;q=0.8",
    ],
)
def test_select_response_format_unsupported(content_type: str) -> None:
    with pytest.raises(errors.UnsupportedSerialization):
        content_negotiation.select_response_format(content_type)
