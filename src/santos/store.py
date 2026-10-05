import sqlite3
from pathlib import Path

from santos.index import ActiveRepo, active_repos

_SCHEMA = """
CREATE TABLE IF NOT EXISTS repos (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    owner TEXT,
    language TEXT,
    current_stars INTEGER,
    description TEXT,
    tracked_since TEXT,
    active INTEGER NOT NULL,
    readme_text TEXT,
    readme_state TEXT NOT NULL,
    etag TEXT
)
"""


def load_membership(db_path: Path, document: object) -> list[ActiveRepo]:
    repos = active_repos(document)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(_SCHEMA)
        for repo in repos:
            conn.execute(
                """
                INSERT INTO repos (
                    id, full_name, owner, language, current_stars,
                    description, tracked_since, active, readme_text,
                    readme_state, etag
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, NULL, 'pending', NULL)
                ON CONFLICT(id) DO UPDATE SET
                    full_name = excluded.full_name,
                    owner = excluded.owner,
                    language = excluded.language,
                    current_stars = excluded.current_stars,
                    description = excluded.description,
                    tracked_since = excluded.tracked_since,
                    active = 1,
                    readme_state = CASE
                        WHEN repos.active = 0 THEN 'pending'
                        ELSE repos.readme_state
                    END
                """,
                (
                    repo.id,
                    repo.full_name,
                    repo.owner,
                    repo.language,
                    repo.current_stars,
                    repo.description,
                    repo.tracked_since,
                ),
            )
        if repos:
            placeholders = ",".join("?" * len(repos))
            conn.execute(
                f"UPDATE repos SET active = 0 WHERE id NOT IN ({placeholders})",
                [repo.id for repo in repos],
            )
        else:
            conn.execute("UPDATE repos SET active = 0")
        conn.commit()
    return repos


def active_readme_targets(db_path: Path) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, full_name, owner, readme_state, etag
            FROM repos
            WHERE active = 1
            ORDER BY id
            """
        ).fetchall()
        return [dict(row) for row in rows]


def record_readme(
    db_path: Path,
    repo_id: int,
    *,
    text: str | None,
    state: str,
    etag: str | None,
) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            UPDATE repos
            SET readme_text = ?, readme_state = ?, etag = ?
            WHERE id = ?
            """,
            (text, state, etag, repo_id),
        )
        conn.commit()


def mark_readme_error(db_path: Path, repo_id: int) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE repos SET readme_state = 'error' WHERE id = ?",
            (repo_id,),
        )
        conn.commit()
