# Spec Delta

## Purpose

Turns each stored README into one vector in the shared 768-d space so a later pitch can find neighbors.

## ADDED Requirements

### Requirement: Embed reads stored README text
`pitch-flap embed` MUST read README text already stored for the active corpus and MUST write one vector for each repo whose README is present. It MUST NOT fetch READMEs and MUST NOT call GitHub Search. When the local corpus is missing, the command MUST fail without writing vectors.

#### Scenario: Present README is embedded
- **WHEN** the user runs `pitch-flap embed` and an active repo has stored README text
- **THEN** the local store has one vector for that repo

#### Scenario: Missing README is skipped
- **WHEN** an active repo is marked missing
- **THEN** the store has no vector for that repo and the command continues

#### Scenario: No corpus yet
- **WHEN** the user runs `pitch-flap embed` and the local corpus does not exist
- **THEN** the command fails and writes no vectors

### Requirement: The model loads at the 8192-token window
The command MUST load `nomic-ai/nomic-embed-text-v1.5` with tokenizer `model_max_length` 8192 and dynamic RoPE (`rope_theta` 1000, factor 2.0). After load, `model_max_length` MUST be 8192. If it is not, the command MUST refuse to embed and MUST leave stored vectors unchanged.

#### Scenario: Window is 8192
- **WHEN** the model finishes loading
- **THEN** `model_max_length` is 8192

#### Scenario: Load stops short of 8192
- **WHEN** `model_max_length` is not 8192 after load
- **THEN** the command writes no vectors

### Requirement: Each vector is the de-normalized 768-d point
For each present README, the command MUST prefix the text with `search_document: `, mean-pool the token embeddings, layer-norm across the 768 dimensions, and store that vector. The stored vector MUST have 768 dimensions. The command MUST NOT L2-normalize it and MUST NOT Matryoshka-truncate it. A README longer than 2048 tokens MUST be truncated at 8192 tokens rather than at 2048.

#### Scenario: Vector matches the pipeline
- **WHEN** a present README is embedded
- **THEN** the stored vector is the mean-pooled, layer-normalized point and is not L2-normalized

#### Scenario: Long README passes 2048 tokens
- **WHEN** a stored README is longer than 2048 tokens
- **THEN** embedding uses the text through the 8192-token window

### Requirement: Embed again only when the input changed
A later `pitch-flap embed` MUST leave a vector in place when the stored README text and the model are unchanged. It MUST replace the vector when the stored text changed or the model changed. Vectors already written MUST remain when a run stops early and the user runs it again.

#### Scenario: Unchanged README
- **WHEN** the user runs embed again and the stored README text and model are unchanged
- **THEN** the stored vector stays the same

#### Scenario: README text changed
- **WHEN** the stored README text for a repo differs from the text that produced its vector
- **THEN** the command replaces that vector

#### Scenario: Model changed
- **WHEN** the loaded model differs from the model that produced the stored vectors
- **THEN** the command re-embeds every present README

#### Scenario: Resume after interruption
- **WHEN** embed stops before every present README has a vector and the user runs it again
- **THEN** vectors already stored are still present and the command finishes the rest

### Requirement: Embed does not pitch
`pitch-flap embed` MUST NOT add Gaussian noise, MUST NOT retrieve neighbors, MUST NOT print a pitch, and MUST NOT record a rating. `pitch-flap refresh` MUST remain free of embedding.

#### Scenario: Embed only writes vectors
- **WHEN** the user runs `pitch-flap embed`
- **THEN** the command does not print a pitch and does not record a rating
