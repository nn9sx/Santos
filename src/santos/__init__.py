"""Santos: the pitch-flap project."""

import sys
from argparse import ArgumentParser
from dotenv import load_dotenv
from os import environ
from pathlib import Path

load_dotenv()
CLI_NAME = "pitch-flap"
XDG_DATA_HOME = environ.get("XDG_DATA_HOME", "")
GITHUB_TOKEN = environ.get("GITHUB_TOKEN", "")

from santos.cli import Refresh
from santos.clients.http import http_fetch


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(prog=CLI_NAME)
    parser.add_argument("command")
    args = parser.parse_args(argv)
    COMMANDS = { "refresh": Refresh }
    if args.command not in COMMANDS: parser.error(f"unknown command {args.command}")
    try:
        COMMANDS[args.command](
            db_path=(Path(XDG_DATA_HOME) if XDG_DATA_HOME else Path.home() / ".local" / "share") / CLI_NAME / "corpus.db",
            fetch=http_fetch
        )()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0
