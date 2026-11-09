import json
import sqlite3

import pytest

from santos import main
from santos.cli.refresh import INDEX_URL
from santos.domains.readme import ReadmeState
from santos.stores.repo import load_membership


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
    monkeypatch.setattr("santos.cli.refresh.GITHUB_TOKEN", "secret")
    monkeypatch.setattr("santos.XDG_DATA_HOME", str(tmp_path))

    def fetch(url, headers):
        if url == INDEX_URL:
            return Response(200, {}, json.dumps(_document()).encode())
        assert url == "https://api.github.com/repos/alice/one/readme"
        assert headers["Authorization"] == "Bearer secret"
        return Response(200, {"etag": '"one"'}, b"# alice")

    monkeypatch.setattr("santos.http_fetch", fetch)
    assert main(["refresh", "--limit", "10"]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""

    db = tmp_path / "pitch-flap" / "corpus.db"
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT id, full_name, active, readme_text, readme_state FROM repos ORDER BY id"
        ).fetchall()
    assert rows == [(1, "alice/one", 1, "# alice", ReadmeState.PRESENT)]


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
    monkeypatch.setattr("santos.cli.refresh.GITHUB_TOKEN", "secret")
    monkeypatch.setattr("santos.XDG_DATA_HOME", str(tmp_path))
    stopped = {"value": True}

    def fetch(url, headers):
        if url == INDEX_URL:
            return Response(200, {}, json.dumps(_two_active()).encode())
        if url.endswith("/alice/one/readme"):
            return Response(200, {"etag": '"alice"'}, b"# alice")
        if url.endswith("/bob/two/readme"):
            if stopped["value"]:
                raise KeyboardInterrupt
            return Response(200, {"etag": '"bob"'}, b"# bob")
        raise AssertionError(url)

    monkeypatch.setattr("santos.http_fetch", fetch)
    with pytest.raises(KeyboardInterrupt):
        main(["refresh", "--limit", "10"])

    db = tmp_path / "pitch-flap" / "corpus.db"
    with sqlite3.connect(db) as conn:
        after_stop = conn.execute(
            "SELECT id, readme_text, readme_state FROM repos ORDER BY id"
        ).fetchall()
    assert after_stop == [(1, "# alice", ReadmeState.PRESENT), (2, None, ReadmeState.PENDING)]

    stopped["value"] = False
    assert main(["refresh", "--limit", "10"]) == 0
    with sqlite3.connect(db) as conn:
        finished = conn.execute(
            "SELECT id, readme_text, readme_state FROM repos ORDER BY id"
        ).fetchall()
    assert finished == [(1, "# alice", ReadmeState.PRESENT), (2, "# bob", ReadmeState.PRESENT)]


def test_second_refresh_replaces_readme_text(tmp_path, monkeypatch):
    monkeypatch.setattr("santos.cli.refresh.GITHUB_TOKEN", "secret")
    monkeypatch.setattr("santos.XDG_DATA_HOME", str(tmp_path))
    body = {"value": b"# old"}
    conditional = []

    def fetch(url, headers):
        if url == INDEX_URL:
            return Response(200, {}, json.dumps(_document()).encode())
        conditional.append(headers.get("If-None-Match"))
        return Response(200, {"etag": '"next"'}, body["value"])

    monkeypatch.setattr("santos.http_fetch", fetch)
    assert main(["refresh", "--limit", "10"]) == 0
    body["value"] = b"# new"
    assert main(["refresh", "--limit", "10"]) == 0

    db = tmp_path / "pitch-flap" / "corpus.db"
    with sqlite3.connect(db) as conn:
        stored = conn.execute("SELECT readme_text, etag FROM repos WHERE id = 1").fetchone()
    assert stored == ("# new", '"next"')
    assert conditional == [None, '"next"']


def test_refresh_and_another_command_are_callable(monkeypatch):
    from santos.cli.command import Command
    from santos.cli import Refresh

    class NeighborPitch(Command):
        def __init__(self) -> None:
            self.called = False

        def __call__(self) -> None:
            self.called = True

    monkeypatch.setattr("santos.cli.refresh.GITHUB_TOKEN", "token")
    refresh = Refresh(db_path="corpus.db", fetch=lambda *_args: None, limit=1)
    pitch = NeighborPitch()
    pitch()

    assert isinstance(refresh, Command)
    assert isinstance(pitch, Command)
    assert pitch.called


def test_refresh_requires_positive_limit(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("santos.cli.refresh.GITHUB_TOKEN", "secret")
    monkeypatch.setattr("santos.XDG_DATA_HOME", str(tmp_path))
    calls = []
    monkeypatch.setattr(
        "santos.http_fetch",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    for argv in (["refresh"], ["refresh", "--limit", "0"], ["refresh", "--limit", "-1"]):
        calls.clear()
        code = main(argv)
        assert code != 0
        assert calls == []
        captured = capsys.readouterr()
        assert "limit" in captured.err.lower()
        assert not (tmp_path / "pitch-flap" / "corpus.db").exists()


def test_refresh_limit_caps_readme_fetches_and_keeps_full_membership(tmp_path, monkeypatch):
    monkeypatch.setattr("santos.cli.refresh.GITHUB_TOKEN", "secret")
    monkeypatch.setattr("santos.XDG_DATA_HOME", str(tmp_path))
    db = tmp_path / "pitch-flap" / "corpus.db"
    load_membership(
        db,
        {
            "count": 4,
            "repos": [
                {
                    "id": 1,
                    "full_name": "a/present",
                    "owner": "a",
                    "language": None,
                    "current_stars": 1,
                    "description": None,
                    "tracked_since": None,
                    "active": True,
                },
                {
                    "id": 2,
                    "full_name": "b/error",
                    "owner": "b",
                    "language": None,
                    "current_stars": 1,
                    "description": None,
                    "tracked_since": None,
                    "active": True,
                },
                {
                    "id": 3,
                    "full_name": "c/pending-low",
                    "owner": "c",
                    "language": None,
                    "current_stars": 1,
                    "description": None,
                    "tracked_since": None,
                    "active": True,
                },
                {
                    "id": 4,
                    "full_name": "d/pending-high",
                    "owner": "d",
                    "language": None,
                    "current_stars": 1,
                    "description": None,
                    "tracked_since": None,
                    "active": True,
                },
            ],
        },
    )
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE repos SET readme_text = ?, readme_state = ?, etag = ? WHERE id = 1",
            ("# present", ReadmeState.PRESENT, '"p"'),
        )
        conn.execute(
            "UPDATE repos SET readme_state = ? WHERE id = 2",
            (ReadmeState.ERROR,),
        )

    fetched = []

    def fetch(url, headers):
        if url == INDEX_URL:
            return Response(
                200,
                {},
                json.dumps(
                    {
                        "count": 4,
                        "repos": [
                            {
                                "id": repo_id,
                                "full_name": name,
                                "owner": name.split("/")[0],
                                "language": None,
                                "current_stars": 1,
                                "description": None,
                                "tracked_since": None,
                                "active": True,
                            }
                            for repo_id, name in (
                                (1, "a/present"),
                                (2, "b/error"),
                                (3, "c/pending-low"),
                                (4, "d/pending-high"),
                            )
                        ],
                    }
                ).encode(),
            )
        fetched.append(url)
        return Response(200, {"etag": '"n"'}, b"# n")

    monkeypatch.setattr("santos.http_fetch", fetch)
    assert main(["refresh", "--limit", "2"]) == 0

    assert fetched == [
        "https://api.github.com/repos/c/pending-low/readme",
        "https://api.github.com/repos/d/pending-high/readme",
    ]
    with sqlite3.connect(db) as conn:
        active = conn.execute(
            "SELECT id, readme_state FROM repos WHERE active = 1 ORDER BY id"
        ).fetchall()
    assert active == [
        (1, ReadmeState.PRESENT),
        (2, ReadmeState.ERROR),
        (3, ReadmeState.PRESENT),
        (4, ReadmeState.PRESENT),
    ]
