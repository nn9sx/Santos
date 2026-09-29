# Spec Delta

## Purpose

Stores README text for the active top-starred repos so a later pitch can name real neighbors.

## ADDED Requirements

### Requirement: Active membership comes from the search index
The refresh command MUST download `https://www.gitstarclub.com/search-index` and MUST treat each object with `active` true as one corpus repo, keyed by its GitHub `id`. It MUST NOT use GitHub Search to choose membership. It MUST leave every other index object out of the active corpus.

#### Scenario: Active row is stored
- **WHEN** the user runs refresh and the index lists a repo with `active` true
- **THEN** the local store has a record for that repo's GitHub `id` and `full_name`

#### Scenario: Inactive row stays out
- **WHEN** the index lists a repo with `active` false
- **THEN** that repo is not in the active corpus

#### Scenario: Index download fails
- **WHEN** the search index cannot be downloaded
- **THEN** the command fails and the previous local store is unchanged

### Requirement: README text is stored or marked missing
For each active repo, the refresh command MUST fetch that repo's README from GitHub and store its text. When GitHub reports that the repo has no README, the command MUST mark that repo missing and MUST continue with the remaining repos.

#### Scenario: README is saved
- **WHEN** GitHub returns a README for an active repo
- **THEN** the stored text is that README

#### Scenario: Missing README
- **WHEN** GitHub reports no README for an active repo
- **THEN** the store marks that repo missing and refresh continues

### Requirement: A later refresh updates the corpus
A later refresh MUST download the index again and MUST make the active corpus match that index's active rows. Stored README text MUST match the README GitHub returns on that run. README text already stored MUST remain when a refresh stops early and the user runs it again.

#### Scenario: README text changed
- **WHEN** a stored README differs from the README GitHub returns on refresh
- **THEN** the stored text becomes the new README

#### Scenario: Repo leaves the active set
- **WHEN** a repo was active and the new index does not list it as active
- **THEN** that repo is not in the active corpus

#### Scenario: Resume after interruption
- **WHEN** refresh stops before every active repo is fetched and the user runs it again
- **THEN** README text already stored is still present and the command continues through the active set

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
- **WHEN** the user runs refresh
- **THEN** the command does not print a pitch and does not record a rating
