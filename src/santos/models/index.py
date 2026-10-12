from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import ClassVar


class IndexDownloadError(Exception):
    """The search index could not be used. The database must stay untouched."""


@dataclass(frozen=True)
class ActiveRepo:
    id: int
    full_name: str
    owner: str | None
    language: str | None
    current_stars: int | None
    description: str | None
    tracked_since: date | None


class ReadmeState(StrEnum):
    PENDING = "pending"
    PRESENT = "present"
    MISSING = "missing"
    ERROR = "error"


@dataclass(frozen=True)
class Repo(ActiveRepo):
    table_name: ClassVar[str] = "repos"
    active: bool
    readme_text: str | None
    readme_state: ReadmeState
    etag: str | None


def _optional_str(repo: dict, key: str) -> str | None:
    value = repo.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise IndexDownloadError(f"active repo {key} is not a string")
    return value


def _optional_date(repo: dict, key: str) -> date | None:
    value = repo.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise IndexDownloadError(f"active repo {key} is not a date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise IndexDownloadError(f"active repo {key} is not a date") from exc


def _optional_int(repo: dict, key: str) -> int | None:
    value = repo.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise IndexDownloadError(f"active repo {key} is not an integer")
    return value


def active_repos(document: object) -> list[ActiveRepo]:
    if not isinstance(document, dict):
        raise IndexDownloadError("search index is not an object")
    repos = document.get("repos")
    count = document.get("count")
    if (
        not isinstance(repos, list)
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count != len(repos)
    ):
        raise IndexDownloadError("count does not match repos")

    active: list[ActiveRepo] = []
    for repo in repos:
        if not isinstance(repo, dict):
            raise IndexDownloadError("repo is not an object")
        if repo.get("active") is not True:
            continue
        repo_id = repo.get("id")
        full_name = repo.get("full_name")
        if isinstance(repo_id, bool) or not isinstance(repo_id, int):
            raise IndexDownloadError("active repo id is not an integer")
        if not isinstance(full_name, str) or full_name.count("/") != 1:
            raise IndexDownloadError("active repo full_name is not owner/repo")
        owner_name, repo_name = full_name.split("/", 1)
        if not owner_name or not repo_name:
            raise IndexDownloadError("active repo full_name is not owner/repo")
        active.append(
            ActiveRepo(
                id=repo_id,
                full_name=full_name,
                owner=_optional_str(repo, "owner"),
                language=_optional_str(repo, "language"),
                current_stars=_optional_int(repo, "current_stars"),
                description=_optional_str(repo, "description"),
                tracked_since=_optional_date(repo, "tracked_since"),
            )
        )
    return active
