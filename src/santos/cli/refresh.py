import json
import time
from http import HTTPStatus

from santos import GITHUB_TOKEN
from santos.cli.command import Command
from santos.domains.readme import fetch_readmes
from santos.models.index import IndexDownloadError
from santos.stores.repo import load_membership

INDEX_URL = "https://www.gitstarclub.com/search-index"


class Refresh(Command):
    def __init__(self, *, db_path, fetch, sleep=None, now=None) -> None:
        self.token = GITHUB_TOKEN.strip()
        if not self.token: raise ValueError("GITHUB_TOKEN is required")
        self.db_path = db_path
        self.fetch = fetch
        self.sleep = time.sleep if sleep is None else sleep
        self.now = time.time if now is None else now

    def __call__(self) -> None:
        try:
            response = self.fetch(
                INDEX_URL,
                {"User-Agent": "pitch-flap", "Accept": "application/json"},
            )
            if response.status != HTTPStatus.OK: raise
            document = json.loads(response.body.decode("utf-8"))
        except Exception as exc:
            raise IndexDownloadError("search index download failed") from exc
        load_membership(self.db_path, document)
        fetch_readmes(self.db_path, self.token, self.fetch, self.sleep, self.now)
