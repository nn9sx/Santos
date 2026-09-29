# Tasks

## 1. Vector math

- [ ] 1.1 Write a failing test that mean-pool and layer-norm of a fixed token matrix produce a 768-d vector that is not L2-normalized. Implement that function, then verify the test passes.

## 2. Model load

- [ ] 2.1 Write a failing test that the load step sets tokenizer `model_max_length` to 8192, `rope_theta` to 1000, and dynamic RoPE factor to 2.0. Implement that configuration, then verify the test passes.
- [ ] 2.2 Write a failing test that a load whose `model_max_length` is not 8192 exits without writing vectors. Implement that guard, then verify the test passes.

## 3. Embedding store

- [ ] 3.1 Write failing tests that a present README gets one vector, a missing README gets none, and a missing corpus database fails without creating vectors. Implement those rules against a temporary copy of the corpus database, then verify the tests pass.
- [ ] 3.2 Write failing tests that an unchanged README keeps its vector, a changed README replaces its vector, and a different model id re-embeds every present README. Implement that, then verify the tests pass.
- [ ] 3.3 Write a failing test that an embed stopped early keeps vectors already stored and a second run finishes the rest. Implement per-row commits, then verify the test passes.

## 4. Embed command

- [ ] 4.1 Write a failing test that `pitch-flap embed` prefixes text with `search_document: `, truncates at 8192 tokens, and prints no pitch. Implement the command on the Santos package, then verify the test passes.
- [ ] 4.2 Write a failing test that `pitch-flap refresh` writes no vectors. Verify that test passes without adding embedding to refresh.

## 5. Integration

- [ ] 5.1 Run the full test suite and verify it exits 0.
