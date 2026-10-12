from pathlib import Path
from sqlalchemy import case, select, update
from sqlalchemy.dialects.sqlite import insert

from santos.models.index import Stub, ReadmeState, Repo, active_repos
from santos.stores.db import engine, repos


def load_membership(db_path: Path, document: object) -> list[Stub]:
    parsed = active_repos(document)
    with engine(db_path).begin() as conn:
        for repo in parsed:
            stmt = insert(repos).values({
                repos.c.id: repo.id,
                repos.c.full_name: repo.full_name,
                repos.c.owner: repo.owner,
                repos.c.language: repo.language,
                repos.c.current_stars: repo.current_stars,
                repos.c.description: repo.description,
                repos.c.tracked_since: repo.tracked_since,
                repos.c.active: True,
                repos.c.readme_text: None,
                repos.c.readme_state: ReadmeState.PENDING,
                repos.c.etag: None,
            })
            excluded = stmt.excluded
            conn.execute(
                stmt.on_conflict_do_update(
                    index_elements=[repos.c.id],
                    set_={
                        repos.c.full_name: excluded.full_name,
                        repos.c.owner: excluded.owner,
                        repos.c.language: excluded.language,
                        repos.c.current_stars: excluded.current_stars,
                        repos.c.description: excluded.description,
                        repos.c.tracked_since: excluded.tracked_since,
                        repos.c.active: True,
                        repos.c.readme_state: case(
                            (repos.c.active == False, ReadmeState.PENDING),
                            else_=repos.c.readme_state,
                        ),
                    },
                )
            )
        if parsed:
            conn.execute(
                update(repos)
                .where(repos.c.id.not_in([repo.id for repo in parsed]))
                .values({repos.c.active: False})
            )
        else:
            conn.execute(update(repos).values({repos.c.active: False}))
    return parsed


def _stored(row) -> Repo:
    return Repo(
        id=row[repos.c.id],
        full_name=row[repos.c.full_name],
        owner=row[repos.c.owner],
        language=row[repos.c.language],
        current_stars=row[repos.c.current_stars],
        description=row[repos.c.description],
        tracked_since=row[repos.c.tracked_since],
        active=row[repos.c.active],
        readme_text=row[repos.c.readme_text],
        readme_state=ReadmeState(row[repos.c.readme_state]),
        etag=row[repos.c.etag],
    )


def active_targets(db_path: Path) -> list[Repo]:
    stmt = (
        select(repos)
        .where(repos.c.active == True)
        .order_by(repos.c.id)
    )
    with engine(db_path).connect() as conn:
        return [_stored(row) for row in conn.execute(stmt).mappings()]


def record_readme(
    db_path: Path,
    repo_id: int,
    *,
    text: str | None,
    state: ReadmeState,
    etag: str | None,
) -> None:
    with engine(db_path).begin() as conn:
        conn.execute(
            update(repos)
            .where(repos.c.id == repo_id)
            .values({
                repos.c.readme_text: text,
                repos.c.readme_state: state,
                repos.c.etag: etag,
            })
        )


def mark_readme_error(db_path: Path, repo_id: int) -> None:
    with engine(db_path).begin() as conn:
        conn.execute(
            update(repos).where(repos.c.id == repo_id).values({repos.c.readme_state: ReadmeState.ERROR})
        )
