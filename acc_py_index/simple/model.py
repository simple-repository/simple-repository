from dataclasses import dataclass
from typing import Optional


@dataclass
class File:
    """Simple representation of a distribution file.
    Defined in PEP-691: https://peps.python.org/pep-0691/
    """

    filename: str
    url: str
    hashes: dict[str, str]  # hash_name to hash_value mapping
    requires_python: Optional[str] = None
    dist_info_metadata: Optional[str] = None  # PEP-658
    gpg_sig: Optional[str] = None
    yanked: Optional[str] = None  # PEP-592: https://peps.python.org/pep-0592/


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
