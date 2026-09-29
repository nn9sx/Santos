# Design

## Context

The repo has no application code. See proposal.md for why the corpus comes first. Specs for this change live in `specs/readme-corpus/spec.md`.

Project context still says GitHub Search builds the index at 25 requests per minute. This design does not do that. Membership is one download of the GitStarClub search index. README bodies come from the GitHub core REST API, which has its own quota.

## Goals / Non-Goals

**Goals:**

- A `pitch-flap refresh` command that fills a local SQLite corpus from the search index and GitHub README responses. The repo and project stay Santos.
- Refresh is safe to re-run: a failed index download does not write, and an interrupted README pass keeps text already stored.
- README traffic backs off from GitHub rate-limit headers.

**Non-Goals:**

- Embeddings, pitches, ratings, and Gaussian noise.
- A schedule. Refresh is a command.
- Filtering catalog or awesome-list repos out of the index.
- Implementing `pull` or any other pitch mode.

## Decisions

### Command

The product and executable are `pitch-flap`. The repo and Python project stay Santos. `pitch-flap refresh` is the only command this change adds. A missing `GITHUB_TOKEN` exits with a non-zero status and a message that a token is required, before any README request and before any database write.

Alternative: make refresh a flag on the default `pull` invocation. Pitch modes are flags, and this step is not a pitch, so it is a separate command.

### Membership

Download `https://www.gitstarclub.com/search-index` into memory. Require a JSON object whose `repos` array length equals `count`. Each active repo must have integer `id` and string `full_name`. Any other shape is a failed download: exit non-zero and do not touch the database.

Keep rows with `active: true`. Persist `id`, `full_name`, `owner`, `language`, `current_stars`, `description`, and `tracked_since`. Set `active` false on stored rows whose id is absent from that active set.

Alternative: shard `GET /search/repositories` by star range. The search index already lists this set, and that sharding was discarded.

### Store

SQLite, through the standard library, at `$XDG_DATA_HOME/pitch-flap/corpus.db` (`~/.local/share/pitch-flap/corpus.db` when `XDG_DATA_HOME` is unset). The primary key is the GitHub numeric `id`, so a renamed `full_name` updates the same row.

README columns: `readme_text`, `readme_state` (`pending`, `present`, `missing`, `error`), and `etag`. New and newly active rows start as `pending`.

Membership updates commit before README fetches. Each README result commits on its own, so a stopped process keeps finished text.

Alternative: one JSON file per repo. SQLite is the project store and can mark the active set in one update.

### README fetch

Sequential `GET https://api.github.com/repos/{owner}/{repo}/readme` with `Authorization: Bearer $GITHUB_TOKEN`, `Accept: application/vnd.github.raw`, `X-GitHub-Api-Version: 2022-11-28`, and a `User-Agent` of `pitch-flap`. The raw media type is the README text to store.

Send `If-None-Match` when the row has an etag. `304` leaves `readme_text` in place. `200` replaces the text, stores the new etag, and sets `present`. `404` sets `missing` and clears the text. `401` aborts the process and keeps rows already written. Other errors retry a small fixed number of times, then set `error` and continue.

On every README response, if `x-ratelimit-remaining` is `0`, sleep until `x-ratelimit-reset`. On `403` or `429`, sleep for `retry-after` when it is present, otherwise until `x-ratelimit-reset`, then retry that repo. Do not apply the 25-requests-per-minute search cap.

A second `pitch-flap refresh` walks the active set again. Pending and error rows are fetched. Present and missing rows are revalidated with conditional requests, which is how stored text stays equal to GitHub without discarding a partial run.

### Tests

Unit tests fake the index HTTP response and the GitHub README API. They do not call either network. A tiny index fixture covers active rows, inactive rows, a bad download, a missing token, `200`, `304`, `404`, and a rate-limit pause.

### Project context files

Update `AGENTS.md` and `openspec/config.yaml` together so the product and CLI are pitch-flap, the repo and project stay Santos, corpus membership is the search-index download, README fetches honor core rate-limit headers, and the 25-per-minute cap stays tied to GitHub Search (which this change does not call).

## Risks / Trade-offs

- [The search-index URL or JSON shape changes] → Treat a shape mismatch as a failed download and leave the previous database alone.
- [The index lags GitHub, including catalog READMEs at the top of the star list] → Store the list as published. Filtering is a later decision.
- [A full refresh still sends one conditional request per active repo, about 5,500 core-API calls] → Sequential requests plus header waits stay inside the authenticated core quota. A token is required so this does not fall through to 60 requests per hour.
- [Secondary rate limits that omit both `retry-after` and `x-ratelimit-reset`] → Retry a small number of times with a short wait, then mark that repo `error` and continue.

## Migration Plan

There is no existing corpus. Installing the package and running `pitch-flap refresh` creates the database. Rollback is deleting that file. No pitch behavior changes, because none exists yet.

## Open Questions

None. Membership URL, the active-row rule, the token requirement, and command-only refresh are decided above.
