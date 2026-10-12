import json
import sqlite3

import pytest

from santos import main
from santos.cli.refresh import INDEX_URL


class Response:
    def __init__(self, status, headers=None, body=b""):
        self.status = status
        self.headers = headers or {}
        self.body = body


def _document():
    return {
        "count": 2,
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
                "language": "Go",
                "current_stars": 4,
                "description": "inactive",
                "tracked_since": None,
                "active": False,
            },
        ],
    }


def test_refresh_fills_store_and_prints_no_pitch(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    def fetch(url, headers):
        if url == INDEX_URL:
            return Response(200, {}, json.dumps(_document()).encode())
        assert url == "https://api.github.com/repos/alice/one/readme"
        assert headers["Authorization"] == "Bearer secret"
        return Response(200, {"etag": '"one"'}, b"# alice")

    monkeypatch.setattr("santos.http_fetch", fetch)
    assert main(["refresh"]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""

    db = tmp_path / "pitch-flap" / "corpus.db"
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT id, full_name, active, readme_text, readme_state FROM repos ORDER BY id"
        ).fetchall()
    assert rows == [(1, "alice/one", 1, "# alice", "present")]


def _two_active():
    return {
        "count": 2,
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
                "language": "Go",
                "current_stars": 4,
                "description": "second",
                "tracked_since": "2021-01-01",
                "active": True,
            },
        ],
    }


def test_refresh_resumes_pending_rows_and_keeps_stored_text(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    stopped = {"value": True}

    def fetch(url, headers):
        if url == INDEX_URL:
            return Response(200, {}, json.dumps(_two_active()).encode())
        if url.endswith("/alice/one/readme"):
            if stopped["value"]:
                return Response(200, {"etag": '"alice"'}, b"# alice")
            assert headers["If-None-Match"] == '"alice"'
            return Response(304, {}, b"")
        if url.endswith("/bob/two/readme"):
            if stopped["value"]:
                raise KeyboardInterrupt
            return Response(200, {"etag": '"bob"'}, b"# bob")
        raise AssertionError(url)

    monkeypatch.setattr("santos.http_fetch", fetch)
    with pytest.raises(KeyboardInterrupt):
        main(["refresh"])

    db = tmp_path / "pitch-flap" / "corpus.db"
    with sqlite3.connect(db) as conn:
        after_stop = conn.execute(
            "SELECT id, readme_text, readme_state FROM repos ORDER BY id"
        ).fetchall()
    assert after_stop == [(1, "# alice", "present"), (2, None, "pending")]

    stopped["value"] = False
    assert main(["refresh"]) == 0
    with sqlite3.connect(db) as conn:
        finished = conn.execute(
            "SELECT id, readme_text, readme_state FROM repos ORDER BY id"
        ).fetchall()
    assert finished == [(1, "# alice", "present"), (2, "# bob", "present")]


def test_second_refresh_replaces_readme_text(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    body = {"value": b"# old"}
    conditional = []

    def fetch(url, headers):
        if url == INDEX_URL:
            return Response(200, {}, json.dumps(_document()).encode())
        conditional.append(headers.get("If-None-Match"))
        return Response(200, {"etag": '"next"'}, body["value"])

    monkeypatch.setattr("santos.http_fetch", fetch)
    assert main(["refresh"]) == 0
    body["value"] = b"# new"
    assert main(["refresh"]) == 0

    db = tmp_path / "pitch-flap" / "corpus.db"
    with sqlite3.connect(db) as conn:
        stored = conn.execute("SELECT readme_text, etag FROM repos WHERE id = 1").fetchone()
    assert stored == ("# new", '"next"')
    assert conditional == [None, '"next"']


def test_refresh_and_another_command_are_callable():
    from santos.cli.command import Command
    from santos.cli import Refresh

    class NeighborPitch(Command):
        def __init__(self) -> None:
            self.called = False

        def __call__(self) -> None:
            self.called = True

    refresh = Refresh(token="token", db_path="corpus.db", fetch=lambda *_args: None)
    pitch = NeighborPitch()
    pitch()

    assert isinstance(refresh, Command)
    assert isinstance(pitch, Command)
    assert pitch.called


