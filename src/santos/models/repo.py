from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import ClassVar


class ReadmeState(StrEnum):
    PENDING = "pending"
    PRESENT = "present"
    MISSING = "missing"
    ERROR = "error"


@dataclass(frozen=True)
class Repo:
    table_name: ClassVar[str] = "repos"
    id: int
    full_name: str
    owner: str | None
    language: str | None
    current_stars: int | None
    description: str | None
    tracked_since: date | None
    active: bool
    readme_text: str | None
    readme_state: ReadmeState
    etag: str | None
