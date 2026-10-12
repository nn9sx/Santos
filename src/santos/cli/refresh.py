import json
import time

from santos.models.index import IndexDownloadError
from santos.domains.readme import fetch_readmes
from santos.stores.repo import load_membership

INDEX_URL = "https://www.gitstarclub.com/search-index"


def refresh(*, token: str, db_path, fetch, sleep=None, now=None) -> None:
    if sleep is None:
        sleep = time.sleep
    if now is None:
        now = time.time
    try:
        response = fetch(
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
    load_membership(db_path, document)
    fetch_readmes(db_path, token, fetch, sleep, now)
