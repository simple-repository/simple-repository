# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import json
import typing

import httpx
import pytest

if typing.TYPE_CHECKING:
    import pathlib

    import pytest_httpx

from .. import errors, utils


@pytest.mark.parametrize(
    ("url", "url_base", "expected_url"),
    [
        ("/relative/path", "https://example.com/", "https://example.com/relative/path"),
        (
            "https://example.com/absolute/path",
            "https://example.com/",
            "https://example.com/absolute/path",
        ),
        ("//example.com/path", "https://example.org/", "https://example.com/path"),
        ("http://example.com/path", "https://example.org/", "http://example.com/path"),
    ],
)
def test_url_absolutizer(url: str, url_base: str, expected_url: str) -> None:
    assert utils.url_absolutizer(url, url_base) == expected_url


@pytest.mark.parametrize(
    "json_string",
    [
        "42",
        "true",
        '["a", "b"]',
        "null",
        '"ciao"',
    ],
)
@pytest.mark.asyncio
async def test_load_config_json_not_a_dict(
    json_string: str,
    tmp_path: pathlib.PosixPath,
) -> None:
    file = tmp_path / "config.json"
    file.write_text(
        data=json_string,
    )
    with pytest.raises(
        errors.InvalidConfigurationError,
        match=(f"Invalid configuration file. {str(file)} must contain a dictionary."),
    ):
        utils.load_config_json(file)


@pytest.mark.asyncio
async def test_load_config_malformed_json(
    tmp_path: pathlib.PosixPath,
) -> None:
    file = tmp_path / "config.json"
    file.write_text(
        data="{",
    )
    with pytest.raises(
        errors.InvalidConfigurationError,
        match=("Invalid json file"),
    ) as exc_info:
        utils.load_config_json(file)
    assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)


@pytest.mark.asyncio
async def test_load_config_file_not_found(
    tmp_path: pathlib.PosixPath,
) -> None:
    file = tmp_path / "config.json"
    with pytest.raises(
        errors.InvalidConfigurationError,
        match=("Configuration file not found"),
    ) as exc_info:
        utils.load_config_json(file)
    assert isinstance(exc_info.value.__cause__, FileNotFoundError)


@pytest.mark.asyncio
async def test_download_file(
    tmp_path: pathlib.PosixPath,
    httpx_mock: pytest_httpx.HTTPXMock,
) -> None:
    download_url = "https://example.com/package.tar.gz"
    dest_file = tmp_path / "package.tar.gz"

    httpx_mock.add_response(content="my_file")
    async with httpx.AsyncClient() as http_client:
        await utils.download_file(download_url, dest_file, http_client)

    assert dest_file.exists()
    assert dest_file.read_text() == "my_file"
