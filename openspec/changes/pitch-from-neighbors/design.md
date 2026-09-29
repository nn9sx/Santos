# Design

## Context

No application code exists yet. See proposal.md for why a pitch needs a center. Specs for this change live in `specs/neighbor-pitch/spec.md`.

`load-readme-corpus` stores repo names. `embed-stored-readmes` stores one 768-d vector per present README. Both require their commands not to pitch. This change does not edit those artifacts.

`pull` still has no noise center. The product CLI is pitch-flap. The repo and project stay Santos.

## Goals / Non-Goals

**Goals:**

- A pitch function that, given a 768-d center and a seed, prints the template from the spec.
- The default command prints no pitch.

**Non-Goals:**

- Choosing a center for `pull`, `topic`, `mood`, `sparse`, `near`, or `mix`.
- `--expand`, Ollama, OpenAI, ratings, and a formula from rating to noise scale.
- Fetching READMEs or embedding text.
- Editing `embed-stored-readmes` or `load-readme-corpus`.

## Decisions

### Entry point

The pitch function takes the center and a seed. Tests call it directly. `pitch-flap` with no arguments exits 0 and writes nothing, so the default command cannot invent `pull`'s center.

Alternative: bind `pull` to the mean of the corpus. That would name a center the project has left open.

### Noise and neighbors

Draw 768 independent samples from `random.Random(seed)` with mean 0 and scale 0.1, and add them to the center. Rank stored vectors by squared Euclidean distance, which preserves Euclidean order, and break ties by ascending GitHub `id`. Take five, or fewer when fewer vectors exist. A repo with no vector is absent from that ranking.

The scale 0.1 and the count five are the assumptions in the proposal. They are constants in this change so tests can lock the template. A later rating change can replace the scale.

Alternative: a numpy index. The corpus is about 5,500 vectors of 768 floats, so a single pass in the standard library is enough and adds no dependency.

### Template

Stdout is exactly `A project near these repos: ` plus the `full_name` values joined by `, `, and a trailing newline. No other sentence is added.

### Store

Read vectors and `full_name` from the corpus database at `$XDG_DATA_HOME/pitch-flap/corpus.db`. Do not write the database. If it is missing, or it contains no vectors, the pitch function fails and prints nothing.

## Risks / Trade-offs

- [Scale 0.1 may be too tight or too wide once real vectors exist] → It is a named constant, covered by a seeded test, and a later change can replace it when ratings exist.
- [The default command does nothing visible] → `pull` has no center yet. Shipping a pitch from a guessed center would freeze that fact.
- [Inactive rows that still have a vector could be named] → Neighbors are whatever vectors are stored. The embed change deletes a vector when a repo leaves the active set.

## Migration Plan

There is no pitch output today. This change adds a function and leaves the default command silent. Rollback is removing that function. Stored vectors are not modified.

## Open Questions

None. The center stays an input, and the template, neighbor count, and noise scale are fixed above.
