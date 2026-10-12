import json
import time

from santos.cli.command import Command
from santos.domains.readme import fetch_readmes
from santos.models.index import IndexDownloadError
from santos.stores.repo import load_membership

INDEX_URL = "https://www.gitstarclub.com/search-index"


class Refresh(Command):
    def __init__(self, *, token: str, db_path, fetch, sleep=None, now=None) -> None:
        self.token = token
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
        except Exception as exc:
            raise IndexDownloadError("search index download failed") from exc
        if getattr(response, "status", None) != 200:
            raise IndexDownloadError("search index download failed")
        try:
            document = json.loads(response.body.decode("utf-8"))
        except (AttributeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IndexDownloadError("search index is not JSON") from exc
        load_membership(self.db_path, document)
        fetch_readmes(self.db_path, self.token, self.fetch, self.sleep, self.now)
