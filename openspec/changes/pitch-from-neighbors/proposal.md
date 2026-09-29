# Proposal

## Why

A pitch is useful only when it names repos that actually sit next to a point in the stored vector space. The corpus and embedding changes keep text and vectors, and both refuse to pitch. This change turns a supplied center into that pitch.

## What Changes

- Given a 768-d center, add isotropic Gaussian noise in that space, take the nearest stored vectors by Euclidean distance, and print a template pitch that names those repos.
- The template is deterministic and includes each neighbor's `full_name`. It does not call Ollama or OpenAI. `--expand` stays a later change.
- Use five neighbors. The initial noise scale is 0.1 per dimension. Both are assumptions recorded for tests, not a tuned product fact.
- Do not choose a center for `pull`, `topic`, `mood`, `sparse`, `near`, or `mix`. `pull`'s noise center stays unspecified. The default command does not print a pitch.
- Do not fetch READMEs, embed text, or change `pitch-flap refresh`.

## Capabilities

### New Capabilities

- `neighbor-pitch`: From a supplied center, noise the point, retrieve Euclidean neighbors, and render a template pitch that names them.

### Modified Capabilities

- None. `load-readme-corpus` and `embed-stored-readmes` already require that refresh and embed do not pitch. Those changes stay as written.

## Impact

- Depends on stored 768-d vectors from `embed-stored-readmes` and repo names from `load-readme-corpus`. No application code exists yet.
- The product CLI is pitch-flap. The repo and project stay Santos.
- No GitHub Search, so the 25-requests-per-minute search cap does not apply.
- Project context still leaves `pull`'s noise center open. This change does not fill that in.

## Success Criteria

- A supplied center yields a template pitch that names the five nearest repos after Gaussian noise, ordered by Euclidean distance.
- The same center and seed yield the same pitch. A missing vector is not a neighbor.
- The default command prints no pitch, because `pull` has no noise center yet.
- The pitch does not call an external model.
- This change does not rate a pitch. When pitches exist, a rating still changes the Gaussian noise on the next run. This change does not define that mechanism, or where `pull` centers its noise.
