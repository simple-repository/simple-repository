from dataclasses import dataclass
from typing import Optional


@dataclass
class File:
    filename: str
    url: str
    hashes: dict[str, str]
    requires_python: Optional[str] = None
    dist_info_metadata: Optional[str] = None
    gpg_sig: Optional[str] = None
    yanked: Optional[str] = None


@dataclass
class Meta:
    api_version: str


@dataclass
class ProjectDetail:
    name: str
    files: list[File]
    meta: Optional[Meta]


@dataclass
class ProjectListElement:
    name: str

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class ProjectList:
    meta: Meta
    projects: set[ProjectListElement]
