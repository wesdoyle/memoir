# agent_notes

## P0 — scaffold + fixture

Decisions
- Layout per initial_prompt.md. `hatchling` is the build backend (uv default; build-time only, not a runtime dep).
- Fixture is built by `tests/fixtures/build_fixture.py` into a temp dir at test time (session-scoped `fixture_repo` in conftest). Not checked in as a repo.
- Fixture uses fixed dates/identities and `HOME`/`GIT_CONFIG_GLOBAL` overrides so user git config (signing, hooks) cannot leak in.
- Fixture history (12 commits) covers every required case: rename (`src/util.py` -> `src/helpers.py`), bot commit (dependabot on requirements.txt), co-authored commit (Dave on core.py), lint sweep by non-expert (Carol, last touch on core.py/helpers.py/README), plus `.mailmap` alias for Bob and one pure `--no-ff` merge. The latter two are not in the P0 list but are hard constraints P1 must test; cost was ~5 lines.
- `tests/test_fixture.py` asserts the fixture's shape via git only (no memoir code yet).

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

## P2 — CLI

Decisions
- `memoir who <path> [-n] [--repo] [--json] [--now]`, `memoir audit [<dir>] [--top 3] [--worst 10] [--repo] [--now]`. `--json` added because rankings must be structured data and it makes the MCP surface a thin wrapper; `--now` for reproducible output/tests.
- `divergence()` lives in scoring.py and is shared by `audit` (P2) and `blame_divergence` (P3). Last committer = raw newest non-merge commit (bots and no-op renames included: that is what `git log -1` shows).
- Audit headline excludes files whose last commit is a bot (reported as a separate count) and files with no human history. Counting bot-last files as "blame lies" would inflate the stat with a trivially true case.
- Worst cases = divergent files sorted by (top expert score - last committer score); last committer with no record scores 0.
- Paths resolve relative to cwd via `git rev-parse --show-toplevel` unless `--repo` is given (then relative to root).

Learnings
- Smoke test on this repo: single author, 0/19 divergence, 0.24 s for 19 files (~12 ms/file, one git process each). P4 repos with 10k+ files will need a path filter or patience; no caching per spec.

## P3 — MCP: skipped at the gate (Wes). Revisit after P4 settles the internals.

## P4 — real repos

Repos (Wes): elastic/elasticsearch, valkey-io/valkey, opencv/opencv, microsoft/vscode, apache/flink. Cloned `--no-checkout --single-branch` into gitignored `eval/repos/` (13 GB free on disk). `audit` now enumerates files with `git ls-tree -r HEAD` so it works without a working tree.

Fixes driven by real repos (each test-first)
- numstat rename form `{old => }` produced `a//b` paths.
- Identity key: email, but name when the email is a placeholder (`no@email`, `(none)`, `localhost`, no domain dot). OpenCV's SVN era had 55 people on `no@email` merged into one "author".
- Bot detection widened: name `bot\b` (OpenCV Pushbot), `^copilot` (1012 vscode commits), `machine$` (elasticsearchmachine, 923 commits). Emails not checked for `bot\b` (geofbot@ is human).
- Human co-authors of bot-authored commits now earn the 0.5 delivery (Copilot commits name the human driver in a trailer).
- `audit` prints divergence among contested files (more than top-n authors) because small files make top-n membership trivial.

Learnings (details and numbers in eval/results.md)
- The 18-month half-life decides almost every ranking on old code. Founders with the highest raw score (antirez 9.9 on server.c, Till Rohrmann 9.4 on JobMaster, Shay Banon on ES core) rank 6th-38th. Whether that is correct depends on what the question is: "who can I ask today" vs "who built the mental model".
- `first_authored` credits whoever made the first commit in git's history: the bulk importer (Erich Gamma on every vscode file, Vadim's 2010 "atomic bomb" in OpenCV), not the author. Unreliable when history begins with an import/restructure.
- Sweeps are the dominant divergence case: one recent 1-2 line commit scores ~1.2, which beats anyone >2 years stale. Josh Soref's spelling sweep is the last commit on 11 of Valkey's 26 divergent src files and sits in the top-3 of 9/30 busiest files.
- Dormant files: all scores collapse toward 0 and order is set by who is least stale, not who knows the code.
- Identity splits remain (Benjamin Pasero: 3 emails, vscode .mailmap does not cover him; Alekhin x3 in OpenCV). Wrong merges are worse than splits, so the fix only targeted merges.
- Cost: one `git log --follow` per file, 0.5-3 s on 100k+ commit repos. Audit scoped to 150-740 file directories.

Open questions — evidence so far
- Q1: Valkey MAINTAINERS.md as partial ground truth: top-1 listed on 21/30 busiest files; 58/90 top-3 slots. Falsification proposal in eval/results.md.
- Q2: last committer is outside top-3 on 0-10% of files (contested: 0-10%) across 10 directories; the differences are almost all signal (sweeps, one-off fixes). But at HL=18 memoir's top-3 is mostly recent committers, so agreement with blame is by construction: contested divergence is 1-4% at HL=18, 8-15% at HL=60, 15-37% with no decay.
- Q3: bots, merges, no-op renames filtered; sweeps and bulk imports are the remaining authorship-without-knowledge cases. Agent-authored commits should credit the human in the trailer (done).
- Q4: decay makes dormant files uninformative; the tool should say "dormant since X, low confidence" and probably show raw ranking.
- Q5: a sweep author in the top-3 is the common mismatch; the file is usually right and the listed roster is per-project, not per-file. Unlisted active contributors (Rain Valentine) are a legitimate disagreement.
- Q6: deferred with P3.

## Perf baseline (eval/perf.md, eval/bench.py)

- Measured before any optimization so later changes have a comparison. `bench.py` attributes git time by wrapping `mining._git` from outside; production code is not instrumented.
- Result: every `who` is one `git log --follow --numstat` that walks the whole commit graph; cost is set by repo history depth (0.15 s valkey .. 2.5 s vscode), not file depth; git is 80-100% of the time. Audit = files × that (6 files/s on valkey).
- One whole-repo `git log --numstat -M` walk on valkey: 6.8 s vs 122 s for 738 per-file walks. Per-file `--follow` is the wrong shape for audit/MCP; see perf.md §5.
- Direction (Wes, 2026-08-21): the no-persistence constraint is relaxed for an on-disk index built from one walk; query-time improvement is the metric. Not yet implemented. Largest repos are not to be benchmarked further.

## Collaboration (how this project is being run; learnings)

- Wes directs at gates, reviews the artifacts, and steers with short directives; the builder proposes the smaller option and records cuts. Gate outputs so far: clamp at 0, no-op commits carry no knowledge, skip P3, raw alongside decayed, relax persistence.
- Commit messages: short subject, body only when it adds information (feedback after P0).
- Measure before optimizing: the perf baseline existed before any change, so P5 has a comparison. Benchmarks use a seeded random sample of 100 files per repo and report mean, median, p95, stdev, min, max (direction 2026-08-21).
- A gut check from Wes ("does git walk the whole graph per file?") caught the per-file `--follow` design flaw that the benchmarks then quantified (18-22x). Architectural sanity checks beat more measurement; raise them early.
- Constraints are revisable by direction when evidence says so (no-persistence -> on-disk index), but the change is recorded here with the date and the reason.
- Real repos found five correctness bugs the synthetic fixture could not; each went fixture/unit test first, then fix, then a separate commit.

## P5 — single walk + persisted index

Decisions
- `mining.walk()`: one streamed `git log --numstat -M --format=...` (optionally pathspec-scoped); rename lineage follows `{old => new}` records backwards from the current path. `mine_file` (per-file `--follow`) is kept as the live fallback and as the reference in tests. Both feed the same `_history_from_commits`, so facts and scoring are unchanged.
- `index.py`: stdlib sqlite3, schema v1 (meta / commits / files), written atomically to `<git-dir>/memoir/index.sqlite` (inside .git: never in the worktree). Rows, not facts, are stored so weights and `now` stay tunable. Freshness = meta head == `rev-parse HEAD`; a pathspec-scoped index reports coverage. Incremental update is a follow-on.
- CLI: `memoir index [dir]`; `who`/`audit` use a fresh covering index silently, announce stale/uncovered fallbacks on stderr, `--live` forces mining, JSON carries `source`.
- Walk vs `--follow` differ on 5/100 seeded valkey files, all explained and all in the walk's favour or neutral: `--follow` follows *copies* (source still exists: sentinel-masters -> sentinel-primaries, hsetex -> msetex, client-setname -> client-capa), one false rename chain (propagate.c <- ... <- zmalloc.h), and a rename-away counted as a 114-line deletion (Makefile). Not adding `-C` (copies) for now.
- Benchmarks: `bench.py build|query|equiv`, seeded 100-file samples, mean/median/p95/stdev/min/max; results in eval/perf.md §6.

