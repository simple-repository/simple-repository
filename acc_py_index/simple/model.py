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
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Union


@dataclass
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
    hashes: dict[str, str]
    requires_python: Optional[str] = None

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
    dist_info_metadata: Optional[Union[bool, dict[str, str]]] = None  # PEP-658

    # PEP-691: An optional key that acts a boolean to indicate if the file has an
    #          associated GPG signature or not.
    # PEP-691: If this key does not exist, then the signature may or may not exist.
    # A None value indicates the key does not exist (i.e. there may or may not be a sig file).
    gpg_sig: Optional[bool] = None

    # PEP-691: either a boolean to indicate if the file has been yanked, or a non empty,
    #          but otherwise arbitrary, string to indicate that a file
    #          has been yanked with a specific reason. If the yanked key is present and
    #          is a [JSON] truthy value, then it SHOULD be interpreted as indicating that
    #          the file pointed to by the url field has been “Yanked”
    # PEP-592: The value of the data-yanked attribute [in HTML], if present, is an
    #          arbitrary string [including falsy ones such as "false"] that represents
    #          the reason for why the file has been yanked.
    # Note that the string "false" is a valid yank reason in both JSON and HTML.
    yanked: Optional[Union[bool, str]] = None

    def __post_init__(self) -> None:
        if self.yanked == "":
            raise ValueError("The yanked attribute may not be an empty string")


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


class ResourceType(Enum):
    REMOTE_RESOURCE = auto()
    METADATA = auto()
    LOCAL_RESOURCE = auto()


@dataclass(frozen=True)
class Resource:
    """Resource downloadable through the index.

    For local resources, no downstream validation is
    performed to ensure that the resource is accessible, so
    they can potentially leak content from the file system.
    """
    value: str
    type: ResourceType
