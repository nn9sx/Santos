import argparse
import os
import sys
from pathlib import Path

from santos.http import http_fetch
from santos.index import IndexDownloadError
from santos.readme import AuthError
from santos.refresh import refresh


def corpus_db_path() -> Path:
    data_home = os.environ.get("XDG_DATA_HOME")
    root = Path(data_home) if data_home else Path.home() / ".local" / "share"
    return root / "pitch-flap" / "corpus.db"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pitch-flap")
    parser.add_argument("command")
    args = parser.parse_args(argv)
    if args.command != "refresh":
        parser.error(f"unknown command {args.command}")
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("A GitHub token is required.", file=sys.stderr)
        return 1
    try:
        refresh(token=token, db_path=corpus_db_path(), fetch=http_fetch)
    except IndexDownloadError:
        print("The search index could not be downloaded.", file=sys.stderr)
        return 1
    except AuthError:
        print("GitHub rejected the token.", file=sys.stderr)
        return 1
    return 0
