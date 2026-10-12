from urllib.parse import quote

from santos.clients.http import header, text
from santos.models.index import ReadmeState
from santos.stores.repo import active_targets, mark_readme_error, record_readme

README_ATTEMPTS = 3
SHORT_WAIT_SECONDS = 1


def _readme_headers(token: str, etag: str | None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.raw",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "pitch-flap",
    }
    if etag: headers["If-None-Match"] = etag
    return headers


def fetch_readmes(db_path, token: str, fetch, sleep, now) -> None:
    for row in active_targets(db_path):
        owner, repo = row.full_name.split("/", 1)
        url = ("https://api.github.com/repos/"f"{quote(owner, safe='')}/{quote(repo, safe='')}/readme")
        headers = _readme_headers(token, row.etag if row.readme_state in (ReadmeState.PRESENT, ReadmeState.MISSING) and row.etag else None)
        response = _fetch_with_retries(url, headers, fetch, sleep, now)
        _apply_readme(db_path, row.id, response)
        _wait_if_exhausted(response, sleep, now)


def _fetch_with_retries(url, headers, fetch, sleep, now):
    last = None
    for attempt in range(1, README_ATTEMPTS + 1):
        try:
            response = fetch(url, headers)
        except Exception:
            response = None
        if response is not None and response.status == 401: raise Exception("GitHub rejected the token")
        if response is not None and response.status in (200, 304, 404): return response
        last = response
        if attempt == README_ATTEMPTS: return last
        _sleep_before_retry(response, sleep, now)
    return last


def _sleep_before_retry(response, sleep, now) -> None:
    if response is None:
        sleep(SHORT_WAIT_SECONDS)
        return
    if response.status in (403, 429):
        retry_after = header(response, "retry-after")
        if retry_after is not None:
            try:
                sleep(float(retry_after))
            except ValueError:
                sleep(SHORT_WAIT_SECONDS)
            return
        if _wait_if_exhausted(response, sleep, now or (lambda: 0)): return
    elif _wait_if_exhausted(response, sleep, now or (lambda: 0)):
        return
    sleep(SHORT_WAIT_SECONDS)


def _wait_if_exhausted(response, sleep, now) -> bool:
    if response is None or now is None: return False
    if header(response, "x-ratelimit-remaining") != "0": return False
    reset = header(response, "x-ratelimit-reset")
    if reset is None: return False
    sleep(max(0, int(reset) - int(now())))
    return True


def _apply_readme(db_path, repo_id: int, response) -> None:
    if response is None or response.status not in (200, 304, 404):
        mark_readme_error(db_path, repo_id)
        return
    if response.status == 304: return
    if response.status == 404:
        record_readme(db_path, repo_id, text=None, state=ReadmeState.MISSING, etag=None)
        return
    record_readme(
        db_path,
        repo_id,
        text=text(response),
        state=ReadmeState.PRESENT,
        etag=header(response, "etag"),
    )
