# Santos

This repo is greenfield. Product facts below are decided. Use them. Ask Andres only when a change cannot proceed without a fact this file leaves open.

## Product

Santos is a CLI that pitches a new project idea grounded in neighboring GitHub READMEs, and names those repos in the pitch.

The user rates pitches. A rating changes the Gaussian noise used on the next run.

Modes are flags. `pull` is the default.

- `pull`: get a pitch
- `topic`: pull clustered to a topic
- `mood`: one of absurd, useful, weekend
- `sparse`: pull from a low-density region
- `near`: pull adjacent to a known project
- `mix`: a power-user blend of pulls

Stack: Python, SQLite, Hugging Face `nomic-ai/nomic-embed-text-v1.5`.

The corpus is local: READMEs for about 1–10k repos. GitHub Search runs while building that index and again on refresh (a command or a schedule). Pace searches at most 25 requests per minute and honor rate-limit headers.

Render a template pitch by default. `--expand` may call Ollama or OpenAI and stays off unless the user passes it.

`pull` does not yet name its noise center. Leave that unspecified until Andres defines it.

## Embeddings

Model: `nomic-ai/nomic-embed-text-v1.5`. 768 dimensions. The window is 8192 tokens, so a normal README is embedded whole. A README that pastes a full API reference can still truncate at 8192.

Load it at that window. Set the tokenizer `model_max_length` to 8192 and dynamic RoPE (`rope_theta` 1000, factor 2.0). Without those, a load can silently stop at 2048. After load, `model_max_length` must be 8192.

Prefix every string with `search_document: `, including topics and known project names. `search_query:` and `clustering:` put the noise center in a different space from the corpus.

Per text:

1. Mean-pool the token embeddings.
2. Layer-norm across the 768 dimensions.
3. Store that vector. This is the de-normalized point. Do not L2-normalize it.
4. Keep all 768 dimensions. A Matryoshka cut happens after layer-norm and breaks the noise scale.

Leave `normalize_embeddings=True` off. That flag L2-normalizes the vector from before layer-norm.

Add Gaussian noise in the stored 768-d space. Where the noise is centered depends on the mode. Find neighbors with Euclidean distance, so a length change from the noise counts. L2-normalize only if a later mode explicitly wants direction-only comparison.

Switching models means re-embedding the corpus. Vectors from another model are not in this space, and the noise scale does not transfer.

## Building

Follow TDD: test, code, refactor (red, green, blue).

When a change is planned as tasks, keep each chunk to at most 2 hours.

## OpenSpec

Schema is spec-driven. `openspec/config.yaml` is injected when drafting artifacts. Follow it, and keep its context and rules out of the artifact text.

Proposals stay under 500 words, tie features to user impact, include a Success Criteria section, and preserve the ratings-to-noise behavior.

On archive, summarize the outcome before finishing.

When this file and `openspec/config.yaml` disagree, update them together. The yaml is what OpenSpec injects. This file is what every coding session should already know.
