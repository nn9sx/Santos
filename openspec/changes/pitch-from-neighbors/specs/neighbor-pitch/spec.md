# Spec Delta

## Purpose

Renders a template pitch that names the repos nearest a noisy point in the stored vector space.

## ADDED Requirements

### Requirement: A supplied center produces a template pitch
Given a 768-d center, the pitch function MUST add isotropic Gaussian noise with scale 0.1 on each dimension, MUST select the nearest stored vectors by Euclidean distance, and MUST print a template pitch naming those repos. The same center and seed MUST produce the same pitch. A center that is not 768-d MUST fail and MUST print no pitch.

#### Scenario: Pitch names the nearest repos
- **WHEN** a 768-d center is supplied and stored vectors exist
- **THEN** the printed pitch names the nearest repos after that noise

#### Scenario: Same inputs repeat
- **WHEN** the same center and seed are supplied again
- **THEN** the printed pitch is identical

#### Scenario: Center has the wrong width
- **WHEN** the supplied center does not have 768 dimensions
- **THEN** the command prints no pitch

### Requirement: The pitch names five neighbors in distance order
The pitch MUST name at most five repos. It MUST order them by ascending Euclidean distance from the noisy point, breaking ties by ascending GitHub `id`. It MUST skip any repo that has no stored vector. When fewer than five vectors exist, it MUST name every repo that has one. When none exist, it MUST fail and MUST print no pitch. The template MUST be `A project near these repos: ` followed by the neighbors' `full_name` values separated by `, `.

#### Scenario: Five neighbors in order
- **WHEN** more than five repos have stored vectors
- **THEN** the pitch names exactly five, nearest first, in that template

#### Scenario: Fewer than five vectors
- **WHEN** only three repos have stored vectors
- **THEN** the pitch names those three and no other repo

#### Scenario: No vectors
- **WHEN** the corpus has no stored vectors
- **THEN** the command prints no pitch

### Requirement: The default command does not choose a center
This change MUST NOT choose a noise center for `pull`, `topic`, `mood`, `sparse`, `near`, or `mix`. The default command MUST print no pitch. The pitch function MUST NOT call Ollama or OpenAI, MUST NOT fetch READMEs, MUST NOT embed text, and MUST NOT record a rating.

#### Scenario: Default command
- **WHEN** the user runs the default command
- **THEN** it prints no pitch

#### Scenario: Template only
- **WHEN** a center is supplied
- **THEN** the pitch is the template and no external model is called
