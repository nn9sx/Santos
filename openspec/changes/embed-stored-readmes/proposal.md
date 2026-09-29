# Proposal

## Why

A pitch can name neighbors only after each stored README is a point in one shared vector space. `pitch-flap refresh` keeps the text and does not embed it, so the next step is to turn that text into vectors.

## What Changes

- Add `pitch-flap embed`. It reads README text already stored by `pitch-flap refresh` and writes one 768-d vector per present README.
- Load `nomic-ai/nomic-embed-text-v1.5` with tokenizer `model_max_length` 8192 and dynamic RoPE (`rope_theta` 1000, factor 2.0). Refuse to embed if `model_max_length` is not 8192 after load.
- Prefix each README with `search_document: `. Mean-pool, layer-norm, and store all 768 dimensions. Do not L2-normalize and do not Matryoshka-truncate.
- Skip missing READMEs. Re-embed when the stored text changes or the model changes. An interrupted run keeps vectors already written.
- Do not add Gaussian noise, retrieve neighbors, or print a pitch. `pitch-flap refresh` still does not embed.

## Capabilities

### New Capabilities

- `readme-embedding`: Embed stored README text into the 768-d space later pitches will search.

### Modified Capabilities

- None. `load-readme-corpus` already requires that refresh does not embed. This change adds a separate command.

## Impact

- Depends on the local corpus from `load-readme-corpus`. No application code exists yet. The product CLI is pitch-flap. The repo and project stay Santos.
- Adds the Hugging Face model as a local dependency. Vectors live in the same SQLite file as the corpus.
- Does not call GitHub Search, so the 25-requests-per-minute search cap does not apply.
- Project context still says GitHub Search builds the corpus. Membership stays with `load-readme-corpus`. This change only embeds text that command stored.

## Success Criteria

- After `pitch-flap embed`, each stored present README has one 768-d vector from that pipeline, and a missing README has none.
- A README longer than 2048 tokens is not cut at 2048.
- A second embed leaves an unchanged README's vector in place and replaces a vector when the text or the model changed.
- The command does not print a pitch or add noise.
- This change does not rate a pitch. When pitches exist, a rating still changes the Gaussian noise on the next run. This change does not define that mechanism, or where `pull` centers its noise.
