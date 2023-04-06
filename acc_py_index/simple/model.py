from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class File:
    """Simple representation of a distribution file.
    Defined in PEP-691: https://peps.python.org/pep-0691/
    """

    filename: str
    url: str

    # Dictionary mapping hash names to a hex encoded digest of the file's hash.
    # Limited to a len() of 1 in HTML. Additional hashes are not included in
    # the HTML serialization.
    hashes: dict[str, str]
    requires_python: Optional[str] = None

    # If dist_info_metadata is present, it MUST be either a boolean to indicate
    # if the file has an associated metadata file, or a dictionary mapping hash
    # names to a hex encoded digest of the metadata’s hash.
    dist_info_metadata: Optional[Union[bool, dict[str, str]]] = None  # PEP-658

    # An optional key that acts a boolean to indicate if the file has an
    # associated GPG signature or not. If this key does not exist, then the
    # signature may or may not exist.
    gpg_sig: Optional[bool] = None

    # yanked, if present, may be either a boolean to indicate if the file has been
    # yanked, or a non empty, but otherwise arbitrary, string to indicate that a file
    # has been yanked with a specific reason. If the yanked key is present and is a
    # truthy value, then it SHOULD be interpreted as indicating that the file pointed to
    # by the url field has been “Yanked” as per PEP 592: https://peps.python.org/pep-0592/.
    yanked: Optional[Union[bool, str]] = None


@dataclass
class Meta:
    """Responses metadata defined in PEP-629:
    https://peps.python.org/pep-0629/
    """
    api_version: str


@dataclass
class ProjectDetail:
    """Model of a project page as described in PEP-691"""
    meta: Meta
    name: str
    files: list[File]


@dataclass(frozen=True)
class ProjectListElement:
    name: str  # not necessarily normalized.


@dataclass
class ProjectList:
    """Model of the project list as described in PEP-691"""
    meta: Meta
    projects: set[ProjectListElement]
