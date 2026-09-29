# Tasks

## 1. Neighbor ranking

- [ ] 1.1 Write a failing test that isotropic Gaussian noise of scale 0.1 is added to a 768-d center and that the same seed repeats the point. Implement that draw, then verify the test passes.
- [ ] 1.2 Write a failing test that the five nearest stored vectors win by Euclidean distance, ties break by ascending GitHub `id`, and a repo with no vector is skipped. Implement that ranking, then verify the test passes.
- [ ] 1.3 Write a failing test that fewer than five vectors names all of them, and that zero vectors fails with no pitch text. Implement that, then verify the test passes.

## 2. Template

- [ ] 2.1 Write a failing test that the pitch text is `A project near these repos: ` plus the neighbor `full_name` values separated by `, `. Implement that template, then verify the test passes.
- [ ] 2.2 Write a failing test that a center that is not 768-d fails and prints no pitch. Implement that guard, then verify the test passes.

## 3. Command

- [ ] 3.1 Write a failing test that `pitch-flap` with no arguments exits 0 and prints no pitch. Implement that default, then verify the test passes.
- [ ] 3.2 Write a failing test that the pitch function reads vectors from a temporary corpus database and does not write that file. Implement that read, then verify the test passes.

## 4. Integration

- [ ] 4.1 Run the full test suite and verify it exits 0.
