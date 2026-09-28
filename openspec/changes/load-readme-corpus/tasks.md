# Tasks

## 1. Package

- [ ] 1.1 Add a Python package that installs a `santos` console script and pytest, and verify `python -m pytest` exits 0 with no failures.

## 2. Search index and store

- [ ] 2.1 Write a failing test that a valid search-index document upserts each `active: true` repo by GitHub `id` and `full_name` into a temporary SQLite file and leaves `active: false` rows out of the active set. Implement that load, then verify the test passes.
- [ ] 2.2 Write a failing test that a download failure or a `count` that disagrees with `repos` leaves an existing database byte-for-byte unchanged. Implement that guard, then verify the test passes.
- [ ] 2.3 Write a failing test that a repo absent from the new active set is no longer active while its stored README text remains. Implement that update, then verify the test passes.

## 3. README fetches

- [ ] 3.1 Write failing tests that a `200` stores the raw README text, a `404` marks the repo missing and continues, and a `304` keeps the stored text. Implement those outcomes, then verify the tests pass.
- [ ] 3.2 Write failing tests that `x-ratelimit-remaining: 0` waits until `x-ratelimit-reset` before the next README request, and that an unset `GITHUB_TOKEN` fetches nothing and reports that a token is required. Implement that behavior, then verify the tests pass.
- [ ] 3.3 Write failing tests that `401` stops the run and keeps rows already stored, and that a repeated non-auth failure marks that repo `error` and continues. Implement that behavior, then verify the tests pass.

## 4. Refresh command

- [ ] 4.1 Write a failing test that `santos refresh` against a fake index and fake GitHub API fills the temporary store and prints no pitch. Implement the command, then verify the test passes.
- [ ] 4.2 Write a failing test that a refresh stopped with rows still `pending`, run again, keeps README text already stored and finishes the active set. Implement resume, then verify the test passes.
- [ ] 4.3 Write a failing test that a second refresh replaces README text when GitHub returns a new body. Implement that revalidation, then verify the test passes.

## 5. Project context

- [ ] 5.1 Update `AGENTS.md` and `openspec/config.yaml` together so corpus membership is `https://www.gitstarclub.com/search-index`, README fetches honor GitHub core rate-limit headers, and the 25-requests-per-minute cap stays on GitHub Search. Verify both files state that same rule.

## 6. Integration

- [ ] 6.1 Run the full test suite and verify it exits 0.
