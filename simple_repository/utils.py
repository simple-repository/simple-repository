# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import json
import pathlib
import typing
from urllib.parse import urljoin, urlparse

import aiohttp

from . import errors


def url_absolutizer(url: str, url_base: str) -> str:
    """Converts a relative url into an absolute one"""
    if not urlparse(url).scheme:
        return urljoin(url_base, url)
    return url


def load_config_json(json_file: pathlib.Path) -> dict[typing.Any, typing.Any]:
    try:
        json_config = json.loads(json_file.read_text())
    except json.JSONDecodeError as e:
        raise errors.InvalidConfigurationError("Invalid json file") from e
    except FileNotFoundError as e:
        raise errors.InvalidConfigurationError("Configuration file not found") from e
    if not isinstance(json_config, dict):
        raise errors.InvalidConfigurationError(
            f"Invalid configuration file. {str(json_file)}"
            " must contain a dictionary.",
        )
    return json_config


async def download_file(
    download_url: str,
    dest_file: pathlib.Path,
    session: aiohttp.ClientSession,
    chunk_size: int = 1024 * 64,
) -> None:
    with dest_file.open('wb') as file:
        async with session.get(download_url) as data:
            async for chunk in data.content.iter_chunked(chunk_size):
                file.write(chunk)
