# Design

## Context

No application code exists yet. See proposal.md for why vectors come after the corpus. `load-readme-corpus` stores README text in SQLite and requires `pitch-flap refresh` not to embed. Specs for this change live in `specs/readme-embedding/spec.md`.

The product CLI is pitch-flap. The repo and project stay Santos. The corpus file is `$XDG_DATA_HOME/pitch-flap/corpus.db`.

## Goals / Non-Goals

**Goals:**

- `pitch-flap embed` writes one 768-d vector per stored present README, using the decided nomic pipeline.
- A second run skips unchanged text and replaces a vector when the text or the model changed.
- An interrupted run keeps vectors already committed.

**Non-Goals:**

- Gaussian noise, neighbor retrieval, pitches, and ratings.
- Embedding inside `pitch-flap refresh`.
- Embedding topics or known project names. Those strings use the same prefix later, when a mode needs them.
- Calling GitHub.

## Decisions

### Command

`pitch-flap embed` is a separate command. If the corpus database is missing, it exits non-zero and does not load the model. `pitch-flap refresh` stays free of this path.

Alternative: embed at the end of refresh. The corpus spec forbids that.

### Model load

Use Hugging Face `transformers` and load `nomic-ai/nomic-embed-text-v1.5`. Before the first forward pass, set the tokenizer `model_max_length` to 8192 and the model RoPE config to `rope_theta` 1000 with dynamic scaling factor 2.0. If `model_max_length` is not 8192 after that, exit non-zero and do not write vectors.

Alternative: `sentence-transformers` with `normalize_embeddings=False`. That flag is exactly the L2 step this pipeline leaves off, and the RoPE settings are easier to assert on the `transformers` load.

### Vector

Prefix the stored README with `search_document: `, including the space. Tokenize with truncation at 8192, so the prefix counts toward the window and a long README is not cut at 2048.

Mean-pool the last hidden state with the attention mask. Layer-norm across the 768 dimensions. Store that float32 vector. Do not L2-normalize it and do not drop dimensions.

### Store

Add an `embeddings` table in the corpus database, keyed by GitHub repo `id`, with `model_id`, `source_digest`, and `vector`. `source_digest` is a hash of the stored README text. A row is current when `model_id` and `source_digest` match. Each finished vector commits on its own.

Delete the vector when the repo is missing or no longer active, so a missing README has no vector. If any stored `model_id` differs from the loaded model, re-embed every present README.

Alternative: a second database. One file keeps the text and the point that was computed from it together.

### Tests

Unit tests do not download weights and do not call the network. They cover mean-pool and layer-norm on a fixed tensor, the `search_document: ` prefix, truncation at 8192, the load guard, skip and replace rules, and that the command prints no pitch.

## Risks / Trade-offs

- [The model weights are large and the first load is slow] → Tests fake the forward pass. A full run is a local batch over about 5,500 short texts, not a GitHub crawl.
- [A README past 8192 tokens is cut] → That is the model window. The stored vector matches the truncated input, and the digest is of the stored README so a later edit still re-embeds.
- [RoPE config names differ by `transformers` version] → The load step must end with `model_max_length` 8192 and the decided `rope_theta` and factor, or it refuses to embed.

## Migration Plan

There is no vector table yet. The first `pitch-flap embed` creates it in the corpus database. Rollback is dropping that table. Refresh behavior does not change.

## Open Questions

None. The model, the window, the pooling, and the separate command are decided above.
