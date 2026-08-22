# agent_notes

## P0 — scaffold + fixture

Decisions
- Layout per initial_prompt.md. `hatchling` is the build backend (uv default; build-time only, not a runtime dep).
- Fixture is built by `tests/fixtures/build_fixture.py` into a temp dir at test time (session-scoped `fixture_repo` in conftest). Not checked in as a repo.
- Fixture uses fixed dates/identities and `HOME`/`GIT_CONFIG_GLOBAL` overrides so user git config (signing, hooks) cannot leak in.
- Fixture history (12 commits) covers every required case: rename (`src/util.py` -> `src/helpers.py`), bot commit (dependabot on requirements.txt), co-authored commit (Dave on core.py), lint sweep by non-expert (Carol, last touch on core.py/helpers.py/README), plus `.mailmap` alias for Bob and one pure `--no-ff` merge. The latter two are not in the P0 list but are hard constraints P1 must test; cost was ~5 lines.
- `tests/test_fixture.py` asserts the fixture's shape via git only (no memoir code yet).

Notes for P1
- Scoring needs an injectable `now` for deterministic tests (fixture dates are fixed; wall clock is not).
- Hand-computed v0 check on core.py with now=2026-08: Alice raw≈6.2 -> ≈1.9 decayed; Carol raw≈2.4 -> ≈0.8. Ranking holds at default weights.

Open questions — evidence so far
- None yet; no real-repo runs until P4. Q3 (authorship-looking commits with no knowledge) is what the Carol/bot fixture cases exercise.
