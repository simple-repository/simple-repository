# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import typing
from urllib.parse import urljoin, urlparse

import httpx

from . import errors


def url_absolutizer(url: str, url_base: str) -> str:
    """Converts a relative url into an absolute one"""
    if not urlparse(url).scheme:
        return urljoin(url_base, url)
    return url


def load_config_json(json_file: pathlib.Path) -> typing.Dict[typing.Any, typing.Any]:
    try:
        json_config = json.loads(json_file.read_text())
    except json.JSONDecodeError as e:
        raise errors.InvalidConfigurationError("Invalid json file") from e
    except FileNotFoundError as e:
        raise errors.InvalidConfigurationError("Configuration file not found") from e
    if not isinstance(json_config, dict):
        raise errors.InvalidConfigurationError(
            f"Invalid configuration file. {str(json_file)} must contain a dictionary.",
        )
    return json_config


async def download_file(
    download_url: str,
    dest_file: pathlib.Path,
    http_client: httpx.AsyncClient,
    chunk_size: int = 1024 * 64,
) -> None:
    with dest_file.open("wb") as file:
        async with http_client.stream("GET", download_url) as data:
            async for chunk in data.aiter_bytes(chunk_size):
                file.write(chunk)


def remove_prefix(source: str, prefix: str) -> str:
    """Compatibility for pre-3.9 implementations that do not have str.removeprefix"""
    if sys.version_info >= (3, 9):
        return source.removeprefix(prefix)
    if source.startswith(prefix):
        return source[len(prefix) :]


def remove_suffix(source: str, suffix: str) -> str:
    """Compatibility for pre-3.9 implementations that do not have str.removesuffix"""
    if sys.version_info >= (3, 9):
        return source.removesuffix(suffix)
    if source.endswith(suffix):
        return source[: -len(suffix)]


def is_relative_to(
    target: pathlib.Path,
    match: typing.Union[str, pathlib.Path],
) -> bool:
    """Compatibility for pre-3.9 implementations that do not have Path.is_relative_to"""
    if sys.version_info >= (3, 9):
        return target.is_relative_to(match)
    try:
        _ = target.relative_to(match)
        return True
    except ValueError:
        return False


def hash_md5(data: bytes) -> str:
    """Compatibility for pre-3.9 implementations that do not allow md5() call with arguments"""
    if sys.version_info >= (3, 9):
        return hashlib.md5(data, usedforsecurity=False).hexdigest()
    h = hashlib.md5()
    h.update(data)
    return h.hexdigest()
