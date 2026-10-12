from pathlib import Path

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    Table,
    Text,
    case,
    create_engine,
    select,
    update,
)
from sqlalchemy.dialects.sqlite import insert

from santos.models.index import ActiveRepo, active_repos

metadata = MetaData()
repos = Table(
    "repos",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("full_name", Text, nullable=False),
    Column("owner", Text),
    Column("language", Text),
    Column("current_stars", Integer),
    Column("description", Text),
    Column("tracked_since", Text),
    Column("active", Integer, nullable=False),
    Column("readme_text", Text),
    Column("readme_state", Text, nullable=False),
    Column("etag", Text),
)


def _engine(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")
    metadata.create_all(engine)
    return engine


def load_membership(db_path: Path, document: object) -> list[ActiveRepo]:
    parsed = active_repos(document)
    with _engine(db_path).begin() as conn:
        for repo in parsed:
            stmt = insert(repos).values(
                id=repo.id,
                full_name=repo.full_name,
                owner=repo.owner,
                language=repo.language,
                current_stars=repo.current_stars,
                description=repo.description,
                tracked_since=repo.tracked_since,
                active=1,
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
                        "active": 1,
                        "readme_state": case(
                            (repos.c.active == 0, "pending"),
                            else_=repos.c.readme_state,
                        ),
                    },
                )
            )
        if parsed:
            conn.execute(
                update(repos)
                .where(repos.c.id.not_in([repo.id for repo in parsed]))
                .values(active=0)
            )
        else:
            conn.execute(update(repos).values(active=0))
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
        .where(repos.c.active == 1)
        .order_by(repos.c.id)
    )
    with _engine(db_path).connect() as conn:
        return [dict(row) for row in conn.execute(stmt).mappings()]


def record_readme(
    db_path: Path,
    repo_id: int,
    *,
    text: str | None,
    state: str,
    etag: str | None,
) -> None:
    with _engine(db_path).begin() as conn:
        conn.execute(
            update(repos)
            .where(repos.c.id == repo_id)
            .values(readme_text=text, readme_state=state, etag=etag)
        )


def mark_readme_error(db_path: Path, repo_id: int) -> None:
    with _engine(db_path).begin() as conn:
        conn.execute(
            update(repos).where(repos.c.id == repo_id).values(readme_state="error")
        )
