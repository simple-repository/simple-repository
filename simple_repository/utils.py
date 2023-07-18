# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from dataclasses import replace
import enum
import functools
import hashlib
import json
import pathlib
import posixpath
import re
import typing
from urllib.parse import urljoin, urlparse

import aiohttp
import fastapi
from fastapi import Request
import packaging.utils
from packaging.version import InvalidVersion, Version

from . import errors
from .simple import model
from .simple.serializer import Format


def url_as_relative(
    destination_absolute_url: str,
    origin_absolute_url: str,
) -> str:
    """Converts, if possible, the destination_absolute_url to a relative to origin_absolute_url"""
    parsed_destination_url = urlparse(destination_absolute_url)
    parsed_origin_url = urlparse(origin_absolute_url)

    if (
        parsed_origin_url.scheme != parsed_destination_url.scheme or
        parsed_origin_url.scheme not in ["http", "https"] or
        parsed_origin_url.netloc != parsed_destination_url.netloc
    ):
        raise ValueError(
            "Cannot create a relative url from "
            f"{origin_absolute_url} to {destination_absolute_url}",
        )

    destination_absolute_path = parsed_destination_url.path
    origin_absolute_path = parsed_origin_url.path

    # Extract all the segments in the url contained between two "/"
    destination_path_tokens = destination_absolute_path.split("/")[1:-1]
    origin_path_tokens = origin_absolute_path.split("/")[1:-1]
    # Calculate the depth of the origin path. It will be the initial
    # number of  dirs to delete from the url to get the relative path.
    dirs_up = len(origin_path_tokens)

    common_prefix = "/"
    for destination_path_token, origin_path_token in zip(
            destination_path_tokens, origin_path_tokens,
    ):
        if destination_path_token == origin_path_token:
            # If the two urls share a parent dir, reduce the number of dirs to delete
            dirs_up -= 1
            common_prefix += destination_path_token + "/"
        else:
            break

    return "../" * dirs_up + destination_absolute_path.removeprefix(common_prefix)


def relative_url_for(
    request: fastapi.Request,
    name: str,
    **kwargs: typing.Any,
) -> str:
    origin_url = str(request.url)
    destination_url = str(request.url_for(name, **kwargs))

    return url_as_relative(
        origin_absolute_url=origin_url,
        destination_absolute_url=destination_url,
    )


def url_absolutizer(url: str, url_base: str) -> str:
    """Converts a relative url into an absolute one"""
    if not urlparse(url).scheme:
        return urljoin(url_base, url)
    return url


def replace_urls(
    project_page: model.ProjectDetail,
    package_name: str,
    request: fastapi.Request,
) -> model.ProjectDetail:
    files = tuple(
        replace(
            file,
            url=relative_url_for(
                request=request,
                name="resources",
                package_name=package_name,
                resource_name=file.filename,
            ),
        ) for file in project_page.files
    )
    return replace(project_page, files=files)


def split_sdist_filename(path: str) -> tuple[str, str]:
    """
    Like os.path.splitext, but take off .tar too.
    Standard functions like splitext or pathlib suffixes
    will fail to extract the extension of sdists
    like numpy-1.0.0.tar.gz
    """
    base, ext = posixpath.splitext(path)
    if base.lower().endswith(".tar"):
        ext = base[-4:] + ext
        base = base[:-4]
    return base, ext


class PackageFormat(enum.Enum):
    WHEEL: str = "wheel"
    SDIST: str = "sdist"
    OTHER: str = "other format"


@functools.lru_cache
def extract_package_format(filename: str) -> PackageFormat:
    _, file_format = split_sdist_filename(filename)
    if file_format == ".whl":
        return PackageFormat.WHEEL
    if file_format in ('.zip', '.tar.gz', '.tar.bz2', '.tar.xz', '.tar.Z', '.tar'):
        return PackageFormat.SDIST
    return PackageFormat.OTHER


def extract_version_from_fragment(fragment: str, project_name: str) -> str:
    def find_version_start() -> int:
        pieces = fragment.split("-")
        for i in range(len(pieces)):
            candidate = "-".join(pieces[0:i])
            if packaging.utils.canonicalize_name(candidate) == project_name:
                return len(candidate)
        raise ValueError(f"{fragment} does not match {project_name}")
    return fragment[find_version_start() + 1:]


@functools.lru_cache
def extract_package_version(filename: str, project_name: str) -> str:
    if extract_package_format(filename) == PackageFormat.WHEEL:
        return filename.split('-')[1]
    else:
        fragment, _ = split_sdist_filename(filename)
        return extract_version_from_fragment(fragment, project_name)


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


PIP_HEADER_REGEX = re.compile(r'^.*?{')


def get_pip_version(
    request: Request,
) -> typing.Optional[Version]:
    if not (pip_header_string := request.headers.get('user-agent', '')):
        return None
    pip_header = PIP_HEADER_REGEX.sub("{", pip_header_string)
    try:
        pip_info = json.loads(pip_header)
    except json.decoder.JSONDecodeError:
        return None
    if not isinstance(pip_info, dict):
        return None

    if implementation := pip_info.get('installer'):
        if isinstance(implementation, dict):
            version_string = implementation.get('version', '')
            try:
                return Version(version_string)
            except InvalidVersion:
                return None
    return None


def sha256sum(file_path: typing.Union[pathlib.Path, str]) -> str:
    sha256 = hashlib.sha256()
    BUF_SIZE = 1024 * 64

    with open(file_path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()


def safe_version(filename: str, project_name: str) -> Version:
    try:
        return Version(
            version=extract_package_version(
                filename=filename,
                project_name=project_name,
            ),
        )
    except (ValueError, InvalidVersion):
        return Version('0.0rc0')
