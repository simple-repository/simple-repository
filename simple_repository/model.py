# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

"""
Models to represent a Simple package index

Essential reading (in order):

 * https://peps.python.org/pep-0503/  (html simple index)
 * https://peps.python.org/pep-0629/  (simple index versioning)
 * https://peps.python.org/pep-0691/  (json simple index)
 * https://peps.python.org/pep-0592/  (yank)
 * https://peps.python.org/pep-0658/  (metadata files)

In general, the model follows the latest PEPs wherever possible, and it is the
responsibility of the parsers and serializers to adapt to the newest standards.

In the comments of this model, we collate the relevant parts of the PEPs.
Direct PEP quotes look like:

    PEP-XXXX: Some directly copy & pasted text from the PEP, which somebody
              could find easily in the PEP with ctrl+F in the browser.

Where additional context is added to a quote, it will be inline within square
brackets, for example ``[additional context]``.

"""

from __future__ import annotations

import dataclasses
from datetime import datetime
import pathlib
import typing

import packaging.utils
import packaging.version

from ._frozen_json import JSONMapping
from ._private_metadata import PrivateMetadataMapping as PrivateMetadataMapping
from ._typing_compat import Protocol, TypedDict
from .packaging import safe_version


@dataclasses.dataclass(frozen=True)
class File:
    """
    Simple representation of a distribution file.
    Defined in PEP-691: https://peps.python.org/pep-0691/
    """

    filename: str
    url: str

    # PEP-592: A dictionary mapping a hash name to a hex encoded digest of the file.
    # PEP-592: Limited to a len() of 1 in HTML
    # Additional hashes are not included in the HTML serialization.
    hashes: typing.Dict[str, str]
    requires_python: typing.Optional[str] = None

    # PEP-691: An optional key that indicates that metadata for this file is available
    # PEP-691: Where this is present, it MUST be either a boolean to indicate
    #          if the file has an associated metadata file, or a dictionary mapping hash
    #          names to a hex encoded digest of the metadata’s hash.
    # PEP-658: The presence [in HTML] of the attribute indicates the distribution
    #          represented by the anchor tag MUST contain a Core Metadata file that
    #          will not be modified when the distribution is processed and/or installed
    # PEP-691: Limited to a len() of 1 in HTML
    # If the key is not "present", it will be None.
    # A maximum of one hash will be included the HTML serialization.
    dist_info_metadata: typing.Union[bool, typing.Dict[str, str], None] = (
        None  # PEP-658
    )

    # PEP-691: An optional key that acts a boolean to indicate if the file has an
    #          associated GPG signature or not.
    # PEP-691: If this key does not exist, then the signature may or may not exist.
    # A None value indicates the key does not exist (i.e. there may or may not be a sig file).
    gpg_sig: typing.Optional[bool] = None

    # PEP-691: either a boolean to indicate if the file has been yanked, or a non empty,
    #          but otherwise arbitrary, string to indicate that a file
    #          has been yanked with a specific reason. If the yanked key is present and
    #          is a [JSON] truthy value, then it SHOULD be interpreted as indicating that
    #          the file pointed to by the url field has been “Yanked”
    # PEP-592: The value of the data-yanked attribute [in HTML], if present, is an
    #          arbitrary string [including falsy ones such as "false"] that represents
    #          the reason for why the file has been yanked.
    # Note that the string "false" is a valid yank reason in both JSON and HTML.
    yanked: typing.Union[bool, str, None] = None

    # PEP-700: This field is mandatory. It MUST contain an integer which is the file size in bytes.
    size: typing.Optional[int] = None

    # PEP-700: This field is optional. If present, it MUST contain a valid ISO 8601 date/time
    #          string, in the format yyyy-mm-ddThh:mm:ss.ffffffZ, which represents the time the
    #          file was uploaded to the index. As indicated by the Z suffix, the upload time
    #          MUST use the UTC timezone.
    upload_time: typing.Optional[datetime] = None

    # PEP-700: Keys (at any level) with a leading underscore are reserved as private for
    # index server use. No future standard will assign a meaning to any such key.
    private_metadata: PrivateMetadataMapping = PrivateMetadataMapping()

    def __post_init__(self) -> None:
        if self.yanked == "":
            raise ValueError("The yanked attribute may not be an empty string")


@dataclasses.dataclass(frozen=True)
class Meta:
    """Responses metadata defined in PEP-629:
    https://peps.python.org/pep-0629/
    """

    api_version: str

    # PEP-700: Keys (at any level) with a leading underscore are reserved as private for
    # index server use. No future standard will assign a meaning to any such key.
    private_metadata: PrivateMetadataMapping = PrivateMetadataMapping()


@dataclasses.dataclass(frozen=True)
class ProjectDetail:
    """Model of a project page as described in PEP-691"""

    meta: Meta
    name: str
    files: typing.Tuple[File, ...]
    # PEP-700: An additional key, versions MUST be present at the top level, in addition to the
    #          keys name, files and meta defined in PEP 691. This key MUST contain a list of version
    #          strings specifying all the project versions uploaded for this project.
    #
    # This field is automatically calculated when a ProjectDetail is created with api_version>=1.1.
    versions: typing.Optional[typing.FrozenSet[str]] = None

    # PEP-700: Keys (at any level) with a leading underscore are reserved as private for
    # index server use. No future standard will assign a meaning to any such key.
    private_metadata: PrivateMetadataMapping = PrivateMetadataMapping()

    def __post_init__(self) -> None:
        api_version = packaging.version.Version(self.meta.api_version)
        if api_version >= packaging.version.Version("1.1"):
            for file in self.files:
                if file.size is None:
                    raise ValueError(
                        "SimpleAPI>=1.1 requires the size field to be set for all the files.",
                    )
            if self.versions is None:
                versions = self.compute_versions_from_files(
                    self.files,
                    self._normalized_name,
                )
                object.__setattr__(self, "versions", versions)

    @classmethod
    def compute_versions_from_files(
        cls,
        files: typing.Tuple[File, ...],
        normalized_name: str,
    ) -> typing.FrozenSet[str]:
        return frozenset(
            str(safe_version(file.filename, normalized_name)) for file in files
        )

    @property
    def _normalized_name(self) -> str:
        return packaging.utils.canonicalize_name(self.name)


@dataclasses.dataclass(frozen=True)
class ProjectListElement:
    name: str  # not necessarily normalized.

    # PEP-700: Keys (at any level) with a leading underscore are reserved as private for
    # index server use. No future standard will assign a meaning to any such key.
    private_metadata: PrivateMetadataMapping = PrivateMetadataMapping()

    @property
    def normalized_name(self) -> str:
        return packaging.utils.canonicalize_name(self.name)


@dataclasses.dataclass(frozen=True)
class ProjectList:
    """Model of the project list as described in PEP-691"""

    meta: Meta
    projects: typing.FrozenSet[ProjectListElement]

    # PEP-700: Keys (at any level) with a leading underscore are reserved as private for
    # index server use. No future standard will assign a meaning to any such key.
    private_metadata: PrivateMetadataMapping = PrivateMetadataMapping()


@dataclasses.dataclass(frozen=True)
class RequestContext:
    context: JSONMapping

    def __init__(
        self,
        context: typing.Union[
            JSONMapping,
            typing.Mapping[str, typing.Any],
        ] = JSONMapping(),
    ) -> None:
        if not isinstance(context, JSONMapping):
            context = JSONMapping.from_any_mapping(context)
        object.__setattr__(self, "context", context)


class Context(TypedDict, total=False):
    etag: str


class Resource(Protocol):
    context: Context
    # If this attribute is set to False, cache components will ignore this resource
    to_cache: bool


@dataclasses.dataclass(frozen=True)
class LocalResource(Resource):
    path: pathlib.Path
    context: Context = dataclasses.field(default_factory=lambda: Context())
    to_cache: bool = dataclasses.field(default=True)


@dataclasses.dataclass(frozen=True)
class HttpResource(Resource):
    url: str
    context: Context = dataclasses.field(default_factory=lambda: Context())
    to_cache: bool = dataclasses.field(default=True)


@dataclasses.dataclass(frozen=True)
class TextResource(Resource):
    text: str
    context: Context = dataclasses.field(default_factory=lambda: Context())
    to_cache: bool = dataclasses.field(default=True)


class NotModified(Exception):
    """
    Exception to be used if the requested resource
    is not changed with respect to the request ETag.
    """
