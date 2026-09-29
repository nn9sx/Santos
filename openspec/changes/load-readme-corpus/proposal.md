# Proposal

## Why

A pitch can name neighboring repos only when their README text is already on disk. Santos has no corpus yet, and the repo list is one JSON file, so the first step is to store those READMEs locally.

## What Changes

- The repo and project stay Santos. The product and its CLI are named pitch-flap.
- Add a `pitch-flap refresh` command that downloads `https://www.gitstarclub.com/search-index` and keeps rows with `active: true`.
- Fetch each repo's README from the GitHub API and store the text in SQLite, with the identity fields from the index.
- On a later refresh, download the index again and update README text. A missing README is recorded and does not abort the run.
- Honor GitHub rate-limit headers on README fetches. Membership is not a GitHub Search.
- Leave embeddings, pitches, and noise for later changes.

Project context still says GitHub Search builds this index and paces searches at 25 requests per minute. This change replaces that for corpus membership: the list comes from the search-index JSON, and README fetches are core API calls.

## Capabilities

### New Capabilities

- `readme-corpus`: Load and refresh a local store of README text for the active repos in the GitStarClub search index.

### Modified Capabilities

- None.

## Impact

- New pitch-flap CLI and a local SQLite database, in the Santos project. No application code exists yet.
- Depends on the GitStarClub search-index URL and the GitHub REST API for README bodies.
- A GitHub token is required so the core rate limit can cover about 5,500 README fetches. Unauthenticated access is 60 requests per hour.
- `AGENTS.md` and `openspec/config.yaml` still describe GitHub Search as the corpus builder and do not name pitch-flap. Update them together so later changes use this product name and do not plan a search indexer.

## Success Criteria

- One refresh command fills SQLite with one row per active search-index repo and the README text GitHub returned, or an explicit missing marker.
- A second refresh updates membership and README text without a GitHub Search query.
- README requests back off when GitHub rate-limit headers say so.
- The user can open the local store and see repo names that a later pitch can cite.
- This change does not rate a pitch. When pitches exist, a rating still changes the Gaussian noise on the next run. This change does not define that mechanism.
