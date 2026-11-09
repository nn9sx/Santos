from dataclasses import dataclass
from urllib.parse import quote

from santos.clients.http import header, text
from santos.models.index import ReadmeState, Repo

README_ATTEMPTS = 3
SHORT_WAIT_SECONDS = 1


@dataclass(frozen=True)
class Readme:
    id: int
    state: ReadmeState
    text: str | None = None
    etag: str | None = None


def _readme_headers(token: str, etag: str | None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.raw",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "pitch-flap",
    }
    if etag: headers["If-None-Match"] = etag
    return headers


def fetch_readmes(targets: list[Repo], token: str, fetch, sleep, now) -> list[Readme]:
    updates: list[Readme] = []
    for row in targets:
        owner, repo = row.full_name.split("/", 1)
        url = ("https://api.github.com/repos/"f"{quote(owner, safe='')}/{quote(repo, safe='')}/readme")
        headers = _readme_headers(token, row.etag if row.readme_state in (ReadmeState.PRESENT, ReadmeState.MISSING) and row.etag else None)
        response = _fetch_with_retries(url, headers, fetch, sleep, now)
        update = _readme_update(row.id, response)
        if update is not None: updates.append(update)
        _wait_if_exhausted(response, sleep, now)
    return updates


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


def _readme_update(repo_id: int, response) -> Readme | None:
    if response is None or response.status not in (200, 304, 404):
        return Readme(id=repo_id, state=ReadmeState.ERROR)
    if response.status == 304: return None
    if response.status == 404:
        return Readme(id=repo_id, state=ReadmeState.MISSING, text=None, etag=None)
    return Readme(
        id=repo_id,
        state=ReadmeState.PRESENT,
        text=text(response),
        etag=header(response, "etag"),
    )
