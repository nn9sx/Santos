from pathlib import Path
from sqlalchemy import case, select, update
from sqlalchemy.dialects.sqlite import insert

from santos.models.index import ActiveRepo, active_repos
from santos.stores.db import engine, repos


def load_membership(db_path: Path, document: object) -> list[ActiveRepo]:
    parsed = active_repos(document)
    with engine(db_path).begin() as conn:
        for repo in parsed:
            stmt = insert(repos).values(
                id=repo.id,
                full_name=repo.full_name,
                owner=repo.owner,
                language=repo.language,
                current_stars=repo.current_stars,
                description=repo.description,
                tracked_since=repo.tracked_since,
                active=True,
                readme_text=None,
                readme_state="pending",
                etag=None,
            )
            excluded = stmt.excluded
            conn.execute(
                stmt.on_conflict_do_update(
                    index_elements=[repos.c.id],
                    set_={
                        "full_name": excluded.full_name,
                        "owner": excluded.owner,
                        "language": excluded.language,
                        "current_stars": excluded.current_stars,
                        "description": excluded.description,
                        "tracked_since": excluded.tracked_since,
                        "active": True,
                        "readme_state": case(
                            (repos.c.active == False, "pending"),
                            else_=repos.c.readme_state,
                        ),
                    },
                )
            )
        if parsed:
            conn.execute(
                update(repos)
                .where(repos.c.id.not_in([repo.id for repo in parsed]))
                .values(active=False)
            )
        else:
            conn.execute(update(repos).values(active=False))
    return parsed


def active_readme_targets(db_path: Path) -> list[dict]:
    stmt = (
        select(
            repos.c.id,
            repos.c.full_name,
            repos.c.owner,
            repos.c.readme_state,
            repos.c.etag,
        )
        .where(repos.c.active == True)
        .order_by(repos.c.id)
    )
    with engine(db_path).connect() as conn:
        return [dict(row) for row in conn.execute(stmt).mappings()]


def record_readme(
    db_path: Path,
    repo_id: int,
    *,
    text: str | None,
    state: str,
    etag: str | None,
) -> None:
    with engine(db_path).begin() as conn:
        conn.execute(
            update(repos)
            .where(repos.c.id == repo_id)
            .values(readme_text=text, readme_state=state, etag=etag)
        )


def mark_readme_error(db_path: Path, repo_id: int) -> None:
    with engine(db_path).begin() as conn:
        conn.execute(
            update(repos).where(repos.c.id == repo_id).values(readme_state="error")
        )
