# readme-corpus

## Purpose

Stores README text for the active top-starred repos so a later pitch can name real neighbors.

## Requirements

### Requirement: Active membership comes from the search index
The refresh command MUST download `https://www.gitstarclub.com/search-index` and MUST treat each object with `active` true as one corpus repo, keyed by its GitHub `id`. It MUST NOT use GitHub Search to choose membership. It MUST leave every other index object out of the active corpus.

#### Scenario: Active row is stored
- **WHEN** the user runs refresh with a valid `--limit` and the index lists a repo with `active` true
- **THEN** the local store has a record for that repo's GitHub `id` and `full_name`

#### Scenario: Inactive row stays out
- **WHEN** the index lists a repo with `active` false
- **THEN** that repo is not in the active corpus

#### Scenario: Index download fails
- **WHEN** the search index cannot be downloaded
- **THEN** the command fails and the previous local store is unchanged

### Requirement: Refresh requires a positive --limit
The refresh command MUST require `--limit` as a positive integer. When `--limit` is omitted or is not a positive integer, the command MUST fail, MUST leave the local store unchanged, MUST NOT download the search index, and MUST NOT fetch READMEs.

#### Scenario: Limit is omitted
- **WHEN** the user runs refresh without `--limit`
- **THEN** the command fails and the local store is unchanged

#### Scenario: Limit is not positive
- **WHEN** the user runs refresh with `--limit` set to zero or a negative integer
- **THEN** the command fails and the local store is unchanged

### Requirement: README text is stored or marked missing
After membership is updated, the refresh command MUST fetch READMEs for at most `--limit` active repos and MUST store each returned text. Targets MUST be chosen in this order: `pending`, then `error`, then `present` and `missing`, and by ascending GitHub `id` within each group. When GitHub reports that the repo has no README, the command MUST mark that repo missing and MUST continue with the remaining targets in this run.

#### Scenario: README is saved
- **WHEN** GitHub returns a README for a selected active repo
- **THEN** the stored text is that README

#### Scenario: Missing README
- **WHEN** GitHub reports no README for a selected active repo
- **THEN** the store marks that repo missing and refresh continues

#### Scenario: Limit caps README fetches
- **WHEN** more than `--limit` active repos still need a fetch in this ordering
- **THEN** the command fetches exactly `--limit` READMEs and leaves the rest for a later refresh

#### Scenario: Fewer targets than the limit
- **WHEN** fewer than `--limit` active repos remain in the fetch ordering
- **THEN** the command fetches every remaining target and succeeds

### Requirement: A later refresh updates the corpus
A later refresh MUST download the index again and MUST make the active corpus match that index's active rows. Within `--limit`, stored README text MUST match the README GitHub returns for the selected targets on that run. README text already stored MUST remain when a refresh stops early and the user runs it again.

#### Scenario: README text changed
- **WHEN** a selected stored README differs from the README GitHub returns on refresh
- **THEN** the stored text becomes the new README

#### Scenario: Repo leaves the active set
- **WHEN** a repo was active and the new index does not list it as active
- **THEN** that repo is not in the active corpus

#### Scenario: Resume after interruption
- **WHEN** refresh stops before every active repo is fetched and the user runs it again with a valid `--limit`
- **THEN** README text already stored is still present and the command continues through the ordered active set within that limit

### Requirement: GitHub rate limits pause README fetches
The refresh command MUST read GitHub rate-limit headers on README requests and MUST wait until the indicated reset before sending another README request when those headers say the quota is exhausted. The command MUST NOT start README fetches when no GitHub token is configured, and MUST tell the user that a token is required.

#### Scenario: Quota exhausted
- **WHEN** a README response says the rate limit is exhausted and names a reset time
- **THEN** the command sends no further README request until that time

#### Scenario: No token
- **WHEN** no GitHub token is configured
- **THEN** the command does not fetch READMEs and reports that a token is required

### Requirement: Refresh does not pitch
The refresh command MUST NOT produce a pitch, MUST NOT embed README text, and MUST NOT record a rating or change Gaussian noise.

#### Scenario: Refresh only loads the corpus
- **WHEN** the user runs refresh with a valid `--limit`
- **THEN** the command does not print a pitch and does not record a rating
