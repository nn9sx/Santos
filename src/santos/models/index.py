from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pydantic import ConfigDict, Field, TypeAdapter, ValidationError, field_validator
from pydantic.dataclasses import dataclass as checked
from typing import Annotated, ClassVar


class IndexDownloadError(Exception):
    """The search index could not be used. The database must stay untouched."""


@checked(frozen=True, config=ConfigDict(extra="ignore"))
class Stub:
    id: Annotated[int, Field(strict=True)]
    full_name: Annotated[str, Field(strict=True)]
    owner: Annotated[str, Field(strict=True)] | None = None
    language: Annotated[str, Field(strict=True)] | None = None
    current_stars: Annotated[int, Field(strict=True)] | None = None
    description: Annotated[str, Field(strict=True)] | None = None
    tracked_since: date | None = None

    @field_validator("tracked_since", mode="before")
    @classmethod
    def _calendar_date(cls, value):
        if value is None: return None
        if not isinstance(value, str): raise ValueError("active repo tracked_since is not a date")
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("active repo tracked_since is not a date") from exc

    @field_validator("full_name")
    @classmethod
    def _owner_repo(cls, value: str) -> str:
        owner_name, separator, repo_name = value.partition("/")
        if separator != "/" or "/" in repo_name or not owner_name or not repo_name:
            raise ValueError("active repo full_name is not owner/repo")
        return value


class ReadmeState(StrEnum):
    PENDING = "pending"
    PRESENT = "present"
    MISSING = "missing"
    ERROR = "error"


@dataclass(frozen=True)
class Repo(Stub):
    table_name: ClassVar[str] = "repos"
    active: bool = False
    readme_text: str | None = None
    readme_state: ReadmeState = ReadmeState.PENDING
    etag: str | None = None

_stub = TypeAdapter(Stub)


def active_repos(document: object) -> list[Stub]:
    if not isinstance(document, dict): raise IndexDownloadError("search index is not an object")
    repos = document.get("repos")
    count = document.get("count")
    if (
        not isinstance(repos, list)
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count != len(repos)
    ): raise IndexDownloadError("count does not match repos")
    active: list[Stub] = []
    for repo in repos:
        if not isinstance(repo, dict): raise IndexDownloadError("repo is not an object")
        if repo.get("active") is not True: continue
        try:
            active.append(_stub.validate_python(repo))
        except ValidationError as exc:
            raise IndexDownloadError("active repo is not usable") from exc
    return active
