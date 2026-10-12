import sqlite3

import pytest

from santos.models.index import IndexDownloadError
from santos.models.repo import ReadmeState
from santos.stores.repo import load_membership


def test_active_rows_are_upserted_by_id_and_full_name(tmp_path):
    db = tmp_path / "corpus.db"
    load_membership(
        db,
        {
            "count": 3,
            "repos": [
                {
                    "id": 1,
                    "full_name": "alice/one",
                    "owner": "alice",
                    "language": "Python",
                    "current_stars": 10,
                    "description": "first",
                    "tracked_since": "2020-01-01",
                    "active": True,
                },
                {
                    "id": 2,
                    "full_name": "bob/two",
                    "owner": "bob",
                    "language": None,
                    "current_stars": 3,
                    "description": None,
                    "tracked_since": None,
                    "active": False,
                },
                {
                    "id": 3,
                    "full_name": "cara/three",
                    "owner": "cara",
                    "language": "Go",
                    "current_stars": 8,
                    "description": "third",
                    "tracked_since": "2021-05-01",
                    "active": True,
                },
            ],
        },
    )

    with sqlite3.connect(db) as conn:
        active = conn.execute(
            "SELECT id, full_name FROM repos WHERE active = 1 ORDER BY id"
        ).fetchall()

    assert active == [(1, "alice/one"), (3, "cara/three")]


def _valid_document():
    return {
        "count": 1,
        "repos": [
            {
                "id": 1,
                "full_name": "alice/one",
                "owner": "alice",
                "language": "Python",
                "current_stars": 10,
                "description": "first",
                "tracked_since": "2020-01-01",
                "active": True,
            }
        ],
    }


def test_count_mismatch_leaves_database_bytes_unchanged(tmp_path):
    db = tmp_path / "corpus.db"
    load_membership(db, _valid_document())
    before = db.read_bytes()

    bad = _valid_document()
    bad["count"] = 99
    with pytest.raises(IndexDownloadError):
        load_membership(db, bad)

    assert db.read_bytes() == before


def test_bad_tracked_since_leaves_database_bytes_unchanged(tmp_path):
    db = tmp_path / "corpus.db"
    load_membership(db, _valid_document())
    before = db.read_bytes()

    bad = _valid_document()
    bad["repos"][0]["tracked_since"] = "not-a-date"
    with pytest.raises(IndexDownloadError):
        load_membership(db, bad)

    assert db.read_bytes() == before


def test_download_failure_does_not_create_or_change_the_database(tmp_path):
    missing = tmp_path / "missing.db"
    with pytest.raises(IndexDownloadError):
        load_membership(missing, None)
    assert not missing.exists()

    db = tmp_path / "corpus.db"
    load_membership(db, _valid_document())
    before = db.read_bytes()
    with pytest.raises(IndexDownloadError):
        load_membership(db, None)
    assert db.read_bytes() == before


def test_absent_repo_is_inactive_and_keeps_readme_text(tmp_path):
    db = tmp_path / "corpus.db"
    load_membership(
        db,
        {
            "count": 2,
            "repos": [
                {
                    "id": 1,
                    "full_name": "alice/one",
                    "owner": "alice",
                    "active": True,
                },
                {
                    "id": 2,
                    "full_name": "bob/two",
                    "owner": "bob",
                    "active": True,
                },
            ],
        },
    )
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE repos SET readme_text = ?, readme_state = ? WHERE id = ?",
            ("stored readme", ReadmeState.PRESENT, 2),
        )

    load_membership(
        db,
        {
            "count": 1,
            "repos": [
                {
                    "id": 1,
                    "full_name": "alice/renamed",
                    "owner": "alice",
                    "active": True,
                }
            ],
        },
    )

    with sqlite3.connect(db) as conn:
        active = conn.execute(
            "SELECT id, full_name FROM repos WHERE active = 1 ORDER BY id"
        ).fetchall()
        kept = conn.execute(
            "SELECT active, readme_text FROM repos WHERE id = 2"
        ).fetchone()

    assert active == [(1, "alice/renamed")]
    assert kept == (0, "stored readme")
