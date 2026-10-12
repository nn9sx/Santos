import sqlite3

import pytest

from santos import main
from santos.domains.readme import fetch_readmes
from santos.models.index import ReadmeState
from santos.stores.repo import load_membership


def _index(*repos):
    return {"count": len(repos), "repos": list(repos)}


def _repo(repo_id, name, **extra):
    owner, repo = name.split("/", 1)
    return {
        "id": repo_id,
        "full_name": name,
        "owner": owner,
        "language": None,
        "current_stars": 1,
        "description": None,
        "tracked_since": None,
        "active": True,
        **extra,
    }


class Response:
    def __init__(self, status, headers=None, body=b""):
        self.status = status
        self.headers = headers or {}
        self.body = body


def _rows(db):
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        return {
            row["id"]: dict(row)
            for row in conn.execute("SELECT * FROM repos ORDER BY id")
        }


def test_readme_outcomes_store_text_mark_missing_and_keep_304(tmp_path):
    db = tmp_path / "corpus.db"
    load_membership(
        db,
        _index(
            _repo(1, "alice/one"),
            _repo(2, "bob/two"),
            _repo(3, "cara/three"),
        ),
    )
    with sqlite3.connect(db) as conn:
        conn.execute(
            """
            UPDATE repos
            SET readme_text = ?, readme_state = ?, etag = ?
            WHERE id = 3
            """,
            ("kept readme", ReadmeState.PRESENT, '"old"'),
        )

    seen = []

    def fetch(url, headers):
        seen.append((url, headers))
        if url.endswith("/alice/one/readme"):
            return Response(200, {"etag": '"one"'}, b"# one")
        if url.endswith("/bob/two/readme"):
            return Response(404, {}, b"")
        if url.endswith("/cara/three/readme"):
            return Response(304, {}, b"")
        raise AssertionError(url)

    fetch_readmes(db, token="token", fetch=fetch, sleep=lambda _seconds: None, now=lambda: 0)

    rows = _rows(db)
    assert rows[1]["readme_text"] == "# one"
    assert rows[1]["readme_state"] == ReadmeState.PRESENT
    assert rows[1]["etag"] == '"one"'
    assert rows[2]["readme_text"] is None
    assert rows[2]["readme_state"] == ReadmeState.MISSING
    assert rows[3]["readme_text"] == "kept readme"
    assert rows[3]["readme_state"] == ReadmeState.PRESENT
    assert [url for url, _headers in seen] == [
        "https://api.github.com/repos/alice/one/readme",
        "https://api.github.com/repos/bob/two/readme",
        "https://api.github.com/repos/cara/three/readme",
    ]
    conditional = seen[2][1]
    assert conditional["If-None-Match"] == '"old"'
    assert conditional["Authorization"] == "Bearer token"
    assert conditional["Accept"] == "application/vnd.github.raw"
    assert conditional["X-GitHub-Api-Version"] == "2022-11-28"
    assert conditional["User-Agent"] == "pitch-flap"
    assert "If-None-Match" not in seen[0][1]


def test_exhausted_rate_limit_waits_until_reset(tmp_path):
    db = tmp_path / "corpus.db"
    load_membership(db, _index(_repo(1, "alice/one"), _repo(2, "bob/two")))
    events = []
    clock = {"now": 1_700_000_000}

    def fetch(url, headers):
        events.append(("fetch", url, clock["now"]))
        if url.endswith("/alice/one/readme"):
            return Response(
                200,
                {
                    "etag": '"one"',
                    "x-ratelimit-remaining": "0",
                    "x-ratelimit-reset": "1700000040",
                },
                b"# one",
            )
        return Response(200, {"etag": '"two"', "x-ratelimit-remaining": "4999"}, b"# two")

    def sleep(seconds):
        events.append(("sleep", seconds))
        clock["now"] += seconds

    fetch_readmes(db, token="token", fetch=fetch, sleep=sleep, now=lambda: clock["now"])

    assert events == [
        ("fetch", "https://api.github.com/repos/alice/one/readme", 1_700_000_000),
        ("sleep", 40),
        ("fetch", "https://api.github.com/repos/bob/two/readme", 1_700_000_040),
    ]


def test_unset_token_fetches_nothing_and_reports_requirement(tmp_path, monkeypatch, capsys):
    data_home = tmp_path / "share"
    monkeypatch.setattr("santos.XDG_DATA_HOME", str(data_home))
    monkeypatch.setattr("santos.load_dotenv", lambda: None)
    calls = []
    monkeypatch.setattr(
        "santos.http_fetch",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    for token in (None, ""):
        calls.clear()
        monkeypatch.setattr("santos.cli.refresh.GITHUB_TOKEN", "")
        code = main(["refresh"])
        assert code != 0
        assert calls == []
        captured = capsys.readouterr()
        assert "token is required" in captured.err.lower()
        assert not (data_home / "pitch-flap" / "corpus.db").exists()


def test_401_stops_and_keeps_rows_already_stored(tmp_path):
    db = tmp_path / "corpus.db"
    load_membership(
        db,
        _index(_repo(1, "alice/one"), _repo(2, "bob/two"), _repo(3, "cara/three")),
    )
    fetched = []

    def fetch(url, headers):
        fetched.append(url)
        if url.endswith("/alice/one/readme"):
            return Response(200, {"etag": '"one"'}, b"# one")
        if url.endswith("/bob/two/readme"):
            return Response(401, {}, b"")
        raise AssertionError(url)

    with pytest.raises(Exception, match="GitHub rejected the token"):
        fetch_readmes(db, token="token", fetch=fetch, sleep=lambda _seconds: None, now=lambda: 0)

    rows = _rows(db)
    assert rows[1]["readme_text"] == "# one"
    assert rows[1]["readme_state"] == ReadmeState.PRESENT
    assert rows[2]["readme_state"] == ReadmeState.PENDING
    assert rows[2]["readme_text"] is None
    assert rows[3]["readme_state"] == ReadmeState.PENDING
    assert fetched == [
        "https://api.github.com/repos/alice/one/readme",
        "https://api.github.com/repos/bob/two/readme",
    ]


def test_repeated_non_auth_failure_marks_error_and_continues(tmp_path):
    db = tmp_path / "corpus.db"
    load_membership(db, _index(_repo(1, "alice/one"), _repo(2, "bob/two")))
    attempts = []

    def fetch(url, headers):
        if url.endswith("/alice/one/readme"):
            attempts.append(url)
            return Response(500, {}, b"")
        return Response(200, {"etag": '"two"'}, b"# two")

    fetch_readmes(db, token="token", fetch=fetch, sleep=lambda _seconds: None, now=lambda: 0)

    rows = _rows(db)
    assert attempts == ["https://api.github.com/repos/alice/one/readme"] * 3
    assert rows[1]["readme_state"] == ReadmeState.ERROR
    assert rows[2]["readme_text"] == "# two"
    assert rows[2]["readme_state"] == ReadmeState.PRESENT

