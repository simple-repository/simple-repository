# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import pytest

from .. import errors
from ..content_negotiation import Format, select_response_format


@pytest.mark.parametrize(
        "content_type, format", [
            ("", Format.HTML_LEGACY),
            ("application/vnd.pypi.simple.v1+html;q=0.8,application/vnd.pypi.simple.v1+json;q=0.9", Format.JSON_V1),
            ("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", Format.HTML_LEGACY),
            ("application/vnd.pypi.simple.v1+html,application/xhtml+xml;q=0.1", Format.HTML_V1),
            ("application/vnd.pypi.simple.v1+json; q = 0.9, application/vnd.pypi.simple.v1+html; q = 0.8", Format.JSON_V1),
        ],
)
def test_select_response_format(content_type: str, format: Format) -> None:
    assert select_response_format(content_type) == format


@pytest.mark.parametrize(
        "content_type", [
            "application/json",
            "application/vnd.pypi.simple.v2+json;q=0.9 , application/vnd.pypi.simple.v2+html;q=0.8",
        ],
)
def test_select_response_format_unsupported(content_type: str) -> None:
    with pytest.raises(errors.UnsupportedSerialization):
        select_response_format(content_type)
