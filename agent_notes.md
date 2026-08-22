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

## P6 — measurement harness and scoring proposals (eval/proposals.md)

- `eval/regress.py run <name> [--set k=v]` / `diff <a> <b>`: audit on the 10 P4 dirs at HL18/HL60/raw, seeded 100-file rank-shift (who entered/left top-3), canaries, regression set, Valkey roster overlap. 7 s per run from the indexes. Baseline saved before any change; re-run after the facts restructure and identical.
- Facts now carry per-touch records (`AuthorFacts.touches`: date, lines, breadth, primary, binary, is_root); index schema v3 adds breadth and parents. Every shape is a `Weights` flag, default off: `breadth_k`, `line_scale`, `line_cap`, `decay_floor`, `decay_depth`, `first_rule`/`first_mass_n`. Per-file `--follow` mining has no breadth, so the discount applies only through the index.
- Findings: breadth discount is the effective sweep fix (Soref 10->4, sweep accounts leave top-3, roster up, audit stat becomes meaningful); line shapes are a smaller overlapping win; decay floor/depth bring founders back but lower roster overlap (current vs built-it is two questions -> two lists); `not_root` fixes the importer case at 6% of files with no canary moves; `not_mass` penalizes Shay Banon's own bulk commits.
- The regression set caught its own weakness: Madelyn Olson's #1 on config.c is held by 0.3 over Binbin (28 commits) on 1,573 lines in 3 commits; breadth and cap both flip it. Reported, not tuned around.
- Dormancy (>36 months idle): `who` says so and orders by raw. Not a score change.
- Subtree merges (valkey deps/jemalloc) leave files with no non-merge history: 16/100 sampled valkey files have no ranking. Known limitation (merges excluded by constraint).
- No defaults changed; recommendations and the replay design are in proposals.md for the gate.

## P7 — adoption, lists, replay

- Adopted defaults: `breadth_k=10`, `line_cap=300`, `first_rule=not_root` (diff_adopted.md). `line_scale` left as a flag (roster -4, replay flat). `V0` constant keeps the spec formula; the regress baseline is V0.
- Fixture consequence of `not_root`: Alice's root-commit creation earns no +3, so Carol's sweep wins README.md and the fixture audit at top-1 is 2/4 (was 3/4). Small real repos with a genuine root-commit creation pay the same price; accepted for the importer case (Gamma 82->0, 6% of P4 files).
- `who --json` now returns `lists` (current / built_it / recent) and `flags` (dormant, last_touch_is_sweep, stability over HL 12/18/36/inf). `Index.history(before=pos)` gives history as of any commit.
- Offline fix-commit replay (eval/replay.py, eval/replay.md): decay validated (raw and hl60 lose everywhere); adopted >= v0; memoir beats last-committer and most-commits by 10-20 points at k=3 everywhere; vs the 3 most recent humans it wins on valkey and vscode, loses narrowly on opencv and flink, ties on ES; at k=1 the last committer is the better single guess on 3/5 repos. The fix criterion is recency-biased; review-routing replay (network) and a deep-bug subset are the next criteria.
- Q1 status: partially answered. The premise survives against naive last-touch; it is not yet shown to beat pure recency (last 3 humans) on the proxy we have.
- Direction (2026-08-22): the fix replay's recency bias and a deep-bug criterion are different heuristics for different questions about human-codebase understanding; worth keeping in mind, but for now simple is better. No further replay criteria; next is review of subtle bugs, then MCP.

## P8 — review fixes (Wes's list), live path removed

- `--live` removed; `who`/`audit` build or refresh the index on demand with a one-line stderr notice (missing, stale, or not covering the path -> full rebuild). One engine; `mine_file` (per-file `--follow`) stays as a library function and the test reference only.
- BOT_NAME_RE tightened: "bot" as its own token / after a separator / in buildbot|pushbot; "machine" as a separate word or the literal elasticsearchmachine. "Matt Talbot", "cccabot", "loopmachine" (1 commit each) are no longer dropped; OpenCV Buildbot/Pushbot, Copilot, Elastic Machine, elasticsearchmachine (923 + 5,272 under a noreply address), Inclusive Coding Bot still are.
- PLACEHOLDER_EMAIL_RE: `unknown` anchored (`^unknown(@|$)`); across the 5 repos all 77 placeholder emails were genuine placeholders, no bad merges found.
- `lists.recent` keyed by identity and emitted as {name, email} like the other lists.
- Erosion was O(authors x touches) per file (server.c: 550k ops, 168 ms per rank()); now a sorted prefix-sum, 2.0 ms, identical results (equality test vs the naive sum).
- regress `diff_fixes.md` vs `adopted`: no movement anywhere.

## P3 (done) — MCP, and incremental index

- `memoir mcp [--repo]` serves exactly three tools over stdio via fastmcp: `who_knows(path, n)` (~120-145 tokens on real files; emails are most of it), `expertise_evidence(path, author)` (substring match on name/email, full record + rank), `blame_divergence(path, n)` (last committer vs top-n with a one-sentence explanation: bot / no-op / sweep / rank). Shared logic moved from cli.py to `api.py` (`Source`, `answer`, `lists_and_flags`, `dormancy`); the spec layout gains that one file.
- Tests use fastmcp's in-memory `Client(server)`; no subprocess.
- Incremental index (direction 2026-08-22): `update_index()` walks only `old_head..HEAD` and prepends the new commits with positions below the current minimum (`pos` is an ordering key, smaller = newer, negative after updates; lineage and `before=` only compare). If HEAD is not a descendant of the indexed commit (rebase/amend) or the schema changed, it rebuilds. `Source` updates when stale, builds when missing or not covering. Correctness test: index at fixture HEAD~6, update to tip, every file identical to a full rebuild (the rename, merge, co-author, bot, and sweep all cross the boundary); amend -> "rebuilt". Cost: 0.13 s (30 commits, valkey), 0.39 s (300, valkey), 0.34 s (300, flink) vs 7-25 s full.
- Caveat: log order within the new batch is by commit date, as in a full walk, but the batch sits above all older rows; a branch renaming a file while mainline kept editing the old name, merged later, can order differently than a full rebuild. Mailmap edits do not re-resolve old rows (rebuild with `memoir index` if needed).

## Proposal — `memoir person` (eval/person.md), not built

- Direction (2026-08-22): if the evidence supports prototyping, build on a new branch, not main. Main holds only the proposal.
- Prototype evidence (scratch, against the indexes): rollup = top files + concentrated directories ranked by expertise mass + TF-IDF themes over path tokens weighted by P's score and file contestedness; vendored trees excluded by default (otherwise importers "own" deps/jemalloc and 3rdparty). Canaries: Madelyn -> acl/config/crc, Viktor -> hashtable/cluster/module, Vadim -> core/imgproc/dnn, antirez -> built_it only (cluster, server, sentinel, replication). Themes are signal with two fixable noise classes (repo-name tokens, test-dir tokens).
- Identity: report-time union over shared email or shared multi-token name; `memoir identities` would emit a tiered .mailmap block for review (high / noreply / names); prototype output looks right on valkey, vscode, opencv.
- Cost: 1-4 ms per file today; candidate discovery must go through forward lineage (Shay Banon's commits sit under pre-rename paths: 11 files by current-name match vs 1,041 by lineage under server/). Proposed: materialize file_lineage and per-file top-5 ranks at build (schema v4; +0.9 ms/file; ES +43 s), now recorded in meta, touched paths recomputed on update, all paths when >30 days old.

## P9 (branch `person`) — memoir person, identities, index v4

- Index schema v4 adds `file_lineage(path, pos)` for every HEAD file and `file_rank` (top-5 current + top-5 raw per file) computed at `rank_now` with `rank_weights` (both in meta). Incremental update: lineage + ranks recomputed for paths touched by the new commits, plus brand-new/renamed-to paths; paths no longer at HEAD pruned; all ranks recomputed when `rank_now` is >30 days from `now` ("reranked", also when HEAD is unchanged). Tests: build matches live `rank()` on every fixture file; incremental == full rebuild on lineage (by sha) and ranks; stale-now rerank.
- `memoir person`: resolution = exact email, else substring with union-find over shared email/normalized name (one group -> merge + note; several -> ambiguous, exit 1). Candidates via `file_lineage` join (forward renames handled: Bob -> helpers.py). Uses materialized ranks when `now` is in the window, else live. Rollup: top files per list, directories by expertise mass with the concentration rule, TF-IDF themes with score x log1p(authors) weighting, IDF floor 0.2, vendored excluded by default.
- `memoir identities`: tiered .mailmap suggestions (high = same multi-token name / noreply login match / one email several spellings); canonical = most commits; never written.
- Measured corrections: basename weighting for themes reverted (worse); IDF floor 0.2 (0.1 drops `cluster`); repo name stop-listed (`opencv`, `valkey`); author count restored for the contested-file weight via file_lineage; strongest row per file when identities are split. Residual theme noise: `server`, `type`, `data`, `support`.
- Cost: person 0.17-0.28 s (valkey/opencv), 1.4 s for Shay Banon on ES (1,488 files; was not findable before lineage); build +7..+23 s per repo; `who`/`audit` unchanged (regress v4 == fixes).

