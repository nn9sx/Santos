from urllib.parse import quote

from santos.stores.repo import active_readme_targets, mark_readme_error, record_readme

README_ATTEMPTS = 3
SHORT_WAIT_SECONDS = 1


class AuthError(Exception):
    """GitHub rejected the token. Rows already stored stay as they are."""


def _header(headers: dict, name: str) -> str | None:
    wanted = name.lower()
    for key, value in headers.items():
        if key.lower() == wanted:
            return value
    return None


def _readme_headers(token: str, etag: str | None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.raw",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "pitch-flap",
    }
    if etag:
        headers["If-None-Match"] = etag
    return headers


def _text(body) -> str:
    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")
    return body


def _conditional_etag(row: dict) -> str | None:
    if row["readme_state"] in ("present", "missing") and row["etag"]:
        return row["etag"]
    return None


def fetch_readmes(db_path, token: str, fetch, sleep, now) -> None:
    for row in active_readme_targets(db_path):
        owner, repo = row["full_name"].split("/", 1)
        url = (
            "https://api.github.com/repos/"
            f"{quote(owner, safe='')}/{quote(repo, safe='')}/readme"
        )
        headers = _readme_headers(token, _conditional_etag(row))
        response = _fetch_with_retries(url, headers, fetch, sleep, now)
        _apply_readme(db_path, row["id"], response)
        _wait_if_exhausted(response, sleep, now)


def _fetch_with_retries(url, headers, fetch, sleep, now):
    last = None
    for attempt in range(1, README_ATTEMPTS + 1):
        try:
            response = fetch(url, headers)
        except Exception:
            response = None
        if response is not None and response.status == 401:
            raise AuthError("GitHub rejected the token")
        if response is not None and response.status in (200, 304, 404):
            return response
        last = response
        if attempt == README_ATTEMPTS:
            return last
        _sleep_before_retry(response, sleep, now)
    return last


def _sleep_before_retry(response, sleep, now) -> None:
    if response is None:
        sleep(SHORT_WAIT_SECONDS)
        return
    if response.status in (403, 429):
        retry_after = _header(response.headers, "retry-after")
        if retry_after is not None:
            try:
                sleep(float(retry_after))
            except ValueError:
                sleep(SHORT_WAIT_SECONDS)
            return
        if _wait_if_exhausted(response, sleep, now or (lambda: 0)):
            return
    elif _wait_if_exhausted(response, sleep, now or (lambda: 0)):
        return
    sleep(SHORT_WAIT_SECONDS)


def _wait_if_exhausted(response, sleep, now) -> bool:
    if response is None or now is None:
        return False
    remaining = _header(response.headers, "x-ratelimit-remaining")
    if remaining != "0":
        return False
    reset = _header(response.headers, "x-ratelimit-reset")
    if reset is None:
        return False
    sleep(max(0, int(reset) - int(now())))
    return True


def _apply_readme(db_path, repo_id: int, response) -> None:
    if response is None or response.status not in (200, 304, 404):
        mark_readme_error(db_path, repo_id)
        return
    if response.status == 304:
        return
    if response.status == 404:
        record_readme(db_path, repo_id, text=None, state="missing", etag=None)
        return
    record_readme(
        db_path,
        repo_id,
        text=_text(response.body),
        state="present",
        etag=_header(response.headers, "etag"),
    )
