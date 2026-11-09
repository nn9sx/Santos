# Design

## Context

The repo has application code for refresh, membership, and README fetch. See proposal.md for why the corpus comes first and why each run must bound README work. Specs for this change live in `specs/readme-corpus/spec.md`.

Project context still says GitHub Search builds the index at 25 requests per minute. This design does not do that. Membership is one download of the GitStarClub search index. README bodies come from the GitHub core REST API, which has its own quota.

## Goals / Non-Goals

**Goals:**

- A `pitch-flap refresh --limit <n>` command that updates local SQLite membership from the search index and fetches at most `n` README responses. The repo and project stay Santos.
- `--limit` is required and must be a positive integer so a first run cannot silently walk the whole active set.
- Refresh is safe to re-run: a failed index download does not write, and an interrupted README pass keeps text already stored.
- README traffic backs off from GitHub rate-limit headers.

**Non-Goals:**

- Embeddings, pitches, ratings, and Gaussian noise.
- A schedule. Refresh is a command (ops may cron it with a fixed `--limit`).
- Filtering catalog or awesome-list repos out of the index.
- Implementing `pull` or any other pitch mode.

## Decisions

### Command

The product and executable are `pitch-flap`. The repo and Python project stay Santos. `pitch-flap refresh` is the only command this change adds. It MUST take `--limit` as a positive integer. When `--limit` is omitted or not a positive integer, exit non-zero before any network call and before any database write.

A missing `GITHUB_TOKEN` exits with a non-zero status and a message that a token is required, after `--limit` is valid and before any README request and before any database write.

Alternative: optional `--limit` with a large default. Rejected so a long first run cannot happen by accident.

Alternative: make refresh a flag on the default `pull` invocation. Pitch modes are flags, and this step is not a pitch, so it is a separate command.

### Membership

Download `https://www.gitstarclub.com/search-index` into memory. Require a JSON object whose `repos` array length equals `count`. Each active repo must have integer `id` and string `full_name`. Any other shape is a failed download: exit non-zero and do not touch the database.

Keep rows with `active: true`. Persist `id`, `full_name`, `owner`, `language`, `current_stars`, `description`, and `tracked_since`. Set `active` false on stored rows whose id is absent from that active set. Membership always covers the full active set for that index download; `--limit` does not cap membership.

Alternative: shard `GET /search/repositories` by star range. The search index already lists this set, and that sharding was discarded.

### Store

SQLite, through SQLAlchemy Core, at `$XDG_DATA_HOME/pitch-flap/corpus.db` (`~/.local/share/pitch-flap/corpus.db` when `XDG_DATA_HOME` is unset). The primary key is the GitHub numeric `id`, so a renamed `full_name` updates the same row.

README columns: `readme_text`, `readme_state` (`pending`, `present`, `missing`, `error`), and `etag`. New and newly active rows start as `pending`.

Membership updates commit before README fetches. Each README result commits on its own, so a stopped process keeps finished text.

Alternative: one JSON file per repo. SQLite is the project store and can mark the active set in one update.

Alternative: one bulk write after every README in the limit window. Rejected because a mid-run stop or `401` would drop that window's progress.

### README fetch

Select at most `--limit` active rows in this order: `pending`, then `error`, then `present` and `missing`, and by ascending GitHub `id` within each group. Sequential `GET https://api.github.com/repos/{owner}/{repo}/readme` with `Authorization: Bearer $GITHUB_TOKEN`, `Accept: application/vnd.github.raw`, `X-GitHub-Api-Version: 2022-11-28`, and a `User-Agent` of `pitch-flap`. The raw media type is the README text to store.

Send `If-None-Match` when the row has an etag and state is `present` or `missing`. `304` leaves `readme_text` in place. `200` replaces the text, stores the new etag, and sets `present`. `404` sets `missing` and clears the text. `401` aborts the process and keeps rows already written. Other errors retry a small fixed number of times, then set `error` and continue.

On every README response, if `x-ratelimit-remaining` is `0`, sleep until `x-ratelimit-reset`. On `403` or `429`, sleep for `retry-after` when it is present, otherwise until `x-ratelimit-reset`, then retry that repo. Do not apply the 25-requests-per-minute search cap.

A later `pitch-flap refresh --limit <n>` downloads the index again, updates membership, and walks the same ordered active set for at most `n` targets. Pending and error rows are fetched first. Present and missing rows are revalidated with conditional requests once earlier groups are drained, which is how stored text stays equal to GitHub without discarding a partial run.

### Tests

Unit tests fake the index HTTP response and the GitHub README API. They do not call either network. A tiny index fixture covers active rows, inactive rows, a bad download, a missing token, missing or non-positive `--limit`, a capped README pass, `200`, `304`, `404`, and a rate-limit pause.

### Project context files

Update `AGENTS.md` and `openspec/config.yaml` together so the product and CLI are pitch-flap, the repo and project stay Santos, corpus membership is the search-index download, README fetches honor core rate-limit headers, and the 25-per-minute cap stays tied to GitHub Search (which this change does not call).

## Risks / Trade-offs

- [The search-index URL or JSON shape changes] → Treat a shape mismatch as a failed download and leave the previous database alone.
- [The index lags GitHub, including catalog READMEs at the top of the star list] → Store the list as published. Filtering is a later decision.
- [Covering ~5,500 READMEs needs many refreshes] → Require `--limit` so each invocation stays bounded; ops can cron or re-run until pending and error are empty.
- [Secondary rate limits that omit both `retry-after` and `x-ratelimit-reset`] → Retry a small number of times with a short wait, then mark that repo `error` and continue.

## Migration Plan

There is no existing corpus. Installing the package and running `pitch-flap refresh --limit <n>` creates the database. Rollback is deleting that file. Existing callers that invoke refresh without `--limit` must pass a positive limit. No pitch behavior changes, because none exists yet.

## Open Questions

None. Membership URL, the active-row rule, the token requirement, required `--limit`, fetch ordering, and command-only refresh are decided above.
