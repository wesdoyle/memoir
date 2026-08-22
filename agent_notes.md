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

## P1 — mining + scoring

Decisions
- One `git log --follow --numstat` call per file (record/unit separators 0x1e/0x1f, numstat rows peeled off the end of `%B` so bodies with blank lines parse). Co-author trailers resolved through `git check-mailmap` in one batched call. No other git calls.
- Identity key = mailmap-resolved email (lowercased); display name from `%aN`.
- Excluded from facts: commits with >1 parent; authors matching the bot regex (name or email). `FileHistory.last_commit` is the raw newest non-merge commit, bots included, so P2 can report what blame shows vs. what memoir says.
- Co-authored commits: 0.5 delivery, no lines credit (cut: weighting lines for co-authors; smaller thing). A co-author who is also the primary author is counted once.
- Dates are author dates (UTC). `active_span` and decay are in months (days/30.4375). `rank()` takes an injectable `now`; defaults to wall clock.
- Evidence record keeps the spec keys plus `raw_score`, `months_since_last_touch`, `others_commits_since` so the formula's terms are inspectable.

Gate decisions (Wes)
- `raw` is clamped at 0 before decay. The formula could go negative (Dave: 1 co-authored commit, 3 later commits by others -> -0.12 on core.py).
- Content-free commits (`added == deleted == 0`, not binary: pure renames, mode changes) carry no knowledge: excluded from deliveries, touches, `first_authored`, and others-since counts. Path lineage is still followed. Smaller than a reduced weight; revisit if real repos show renames that do carry knowledge (e.g. module restructuring by the owner). `Commit.is_noop` marks them; `raw_score` still visible in evidence.

Open questions — evidence so far
- Q3: bots and merges are filtered; lint sweeps and renames are not — they count as deliveries, relying on `first_authored` + delivery count + size to outweigh them. Fixture confirms at default weights (Alice 1.87 vs Carol 0.77).
