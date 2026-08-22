# Evaluation results (P4, v0)

Run date: 2026-08-21. Repos (full history, `--no-checkout --single-branch`): elastic/elasticsearch (104,744 commits), valkey-io/valkey (14,019), opencv/opencv (37,642), microsoft/vscode (163,752), apache/flink (38,347). Defaults: `w_first=3, w_del=1, w_size=0.5, w_decay=0.7, HALF_LIFE=18 mo`. One `git log --follow --numstat` per file costs 0.5-3 s on the 100k+ commit repos, so audits are scoped to directories.

## 1. Audit: how often does the last committer fall outside memoir's top-3?

"Contested" = files with more than 3 human authors (top-3 membership is trivial otherwise). Bot-last-touch files are excluded from the headline.

| repo | directory | files | blame lies (all) | contested | notes |
|---|---|---|---|---|---|
| valkey | src | 738 | 26/738 (3.5%) | 26/668 (3.9%) | 11 of 26 are Josh Soref's spelling sweep; the rest one-off fixes (Shun Takahashi ×4, Satheesha CH Gowda ×2) |
| opencv | modules/core/src | 191 | 5/191 (2.6%) | 3/117 (2.6%) | |
| opencv | modules/imgproc/src | 141 | 5/139 (3.6%) | 5/99 (5.1%) | `imgwarp.cpp`: last 熊阔豪 (1.38) vs Vadim Pisarevsky (4.75) |
| flink | runtime/checkpoint | 146 | 1/146 (0.7%) | 1/106 (0.9%) | |
| flink | runtime/jobmaster | 110 | 0/110 (0.0%) | 0/70 (0.0%) | |
| flink | runtime/executiongraph | 85 | 0/85 (0.0%) | 0/69 (0.0%) | |
| elasticsearch | cluster | 387 | 21/387 (5.4%) | 21/297 (7.1%) | `MetadataMappingService`: last Anton Persson (1.60) vs David Turner (5.00); `DiskThresholdDecider`, `DiscoveryNodes`, `DesiredBalanceComputer` all David Turner vs a recent one-off |
| elasticsearch | index/engine | 54 | 3/54 (5.6%) | 3/44 (6.8%) | `InternalEngine.java`: last Anantha Krishnan S R (1.03) vs Tim Brooks (5.82) |
| vscode | src/vs/editor/common | 232 | 8/229 (3.5%) | 7/179 (3.9%) | 3 bot-last files excluded; `editorOptions.ts`: last Paul (1.74) vs Alexandru Dima (9.16); `editorCommon.ts` Dima 6.67 vs Matt Bierner 0.83 |
| vscode | src/vs/base/common | 161 | 12/158 (7.6%) | 11/110 (10.0%) | 3 bot-last excluded; `resources.ts`: last dileepyavan (1.13) vs Martin Aeschlimann (5.11); `map.ts`, `arrays.ts`, `uri.ts`: Johannes Rieken vs one-off fixes |

Reading: the rate is low everywhere. That is not because blame is honest; it is because an 18-month half-life makes memoir's top-3 ≈ "the most recent substantive committers", which is close to what blame shows. The divergent cases are almost entirely sweeps and one-off fixes, i.e. real signal, but the formula leaves little room to disagree with blame on active files. Divergence under alternative half-lives (analysis only, no tool change):

| directory | HL=18 (v0) | HL=60 | raw (no decay) | creator in top-3: HL=18 / HL=60 / raw |
|---|---|---|---|---|
| valkey src (668 contested) | 26 (3.9%) | 66 (9.9%) | 99 (14.8%) | 587/738 · 702/738 · 738/738 |
| opencv modules/core/src (117) | 3 (2.6%) | 10 (8.5%) | 39 (33.3%) | 120/191 · 158/191 · 190/191 |
| flink runtime/checkpoint (106) | 1 (0.9%) | 16 (15.1%) | 39 (36.8%) | 79/146 · 132/146 · 144/146 |

The headline stat is mostly a function of the half-life. At HL=18 memoir and blame agree ~96-99% of the time; without decay they disagree 15-37% of the time and the creator is almost always in the top-3. Neither extreme is obviously right — the two rankings answer different questions ("who is current" vs "who built it") — but v0's default sits at the end where the tool adds least over `git log -1`.

## 2. Surprising rankings

Decayed = v0 score; raw = before decay. "creator" = author of the first commit in `--follow` history.

1. **Departed founders rank 6th-38th despite the highest raw scores.** valkey `src/server.c`: antirez raw 9.88 (created, 778 commits, 15k lines, last touch 2020) → score 0.56, rank 25; top is Binbin (85 commits, 6.63). Same on `cluster_legacy.c` (rank 20), `dict.c` (15), `sds.c` (12), `ae.c` (7). flink `JobMaster.java`: Till Rohrmann raw 9.41 (created, 125 commits) rank 6 behind Yi Zhang (2 commits, 11 lines, score 1.90). elasticsearch: Shay Banon is creator of `IndexMetadata`, `InternalEngine`, `SearchService`, `Node` and ranks 32-38 on each (last touch 2015). Whether this is right depends on the question: "who can I ask today" (decayed) vs "who built the mental model" (raw).
2. **`first_authored` credits the importer, not the author.** vscode: Erich Gamma is "creator" of every file examined (2015-11-13 initial import, 1 commit each). OpenCV: Vadim Pisarevsky's 2010 "atomic bomb" restructure commit (root of the git history) — correct by luck. flink `ExecutionGraph.java`: "StephanEwen" (2014, unmailmapped variant of Stephan Ewen). Bulk imports and history rewrites make the +3.0 term land on the wrong person.
3. **A single recent 1-2 line commit scores ~1.2, which beats any author more than ~2 years stale.** Josh Soref's spelling sweeps (6 commits, ~140 files, 2026-08-11..13) are the last commit on 11 of Valkey's 26 divergent `src` files and place him in the top-3 of 9 of the 30 busiest files (`ae.c` rank 2, `t_stream.c`, `bitops.c` rank 1). Same shape: Shun Takahashi, Satheesha CH Gowda in the Valkey worst-cases list.
4. **One huge commit ranks #2.** valkey `t_zset.c`: Ran Shidlansik, 1 commit, 1293 lines → 4.14, above Binbin (22 commits). The size term is unbounded in lines; a refactor/format commit can buy a top slot.
5. **Dormant files are noise.** valkey `src/lzf_c.c` (last touch 2021): sundb 0.22 (1 commit, 13 lines) > Ozan Tezcan 0.16 > antirez 0.02 (created, 303 lines). Order is "least stale", not "knows the code". `setcpuaffinity.c`: same.
6. **Identity.** Without `.mailmap` (valkey, opencv, flink, elasticsearch have none): antirez split 2 ways, Alexander Alekhin 3 ways (opencv `dnn.cpp` has him at rank 1 and 3), Stephan Ewen/StephanEwen, Megan Rogge/meganrogge (vscode, despite a `.mailmap`), Benjamin Pasero 3 emails (vscode `workbench.ts` ranks 1 and 3). OpenCV's SVN-era `no@email` placeholder (55 people) had collapsed into one author before the fix in this phase.
7. **Agents and automation.** vscode: 1012 Copilot-authored commits (two author names, one email); their trailers name the human driver (meganrogge 175, TylerLeonhardt 142). elasticsearch: `elasticsearchmachine` 923 commits (Lucene snapshot bumps, test mutes, merges). OpenCV: `OpenCV Pushbot`/`Buildbot`. All now filtered; human co-authors of bot commits credited at 0.5.
8. **Path artifacts.** flink's `{rpc => }` rename form produced `runtime//jobmaster` paths before the fix.

Rankings that looked right: vscode `textModel.ts` (Alex Dima 212 commits, 8.01), `event.ts` (Johannes Rieken), `terminal.ts` (Megan Rogge, Daniel Imms); elasticsearch `Node.java` (David Turner, Ryan Ernst); opencv `matrix.cpp` (Vadim Pisarevsky, 5.91, with a 4× margin); valkey `config.c` (Madelyn Olson), `dict.c` (Viktor Söderqvist).

## 3. Open question 5: memoir vs. the roster

Valkey `MAINTAINERS.md` lists 12 maintainers+committers. On the 30 busiest `src/*.c` files: memoir's top-1 is listed on 21/30; 58/90 top-3 slots are listed people. Misses: (a) sweep authors (Josh Soref, 9 files) — the roster is right; (b) Rain Valentine (unlisted, many substantive recent commits on `t_zset.c`, `object.c`, `aof.c`) — memoir is plausibly right about the file and the roster is per-project, not per-file; (c) `commands.c` (guybe7, Daniil Kashapov, Oran Agra — the Redis-era generator authors, 0/3) — both are right about different questions. Elasticsearch and vscode have `CODEOWNERS` (team handles, not people) — not comparable without a team→people map. OpenCV and Flink have no roster.

## 4. Open question 1: validating or falsifying the premise (proposal only)

The premise: git history, mined deterministically, ranks people by how well they hold a file's mental model, and that ranking is more useful than last-touch. Ground truth candidates, cheapest first:

1. **Roster overlap (weak, available now).** Per-file top-k vs MAINTAINERS/CODEOWNERS/AUTHORS where they exist. Valkey gives 21/30. Weak because rosters are project-level and lag reality. Use as a sanity floor, not a target.
2. **Review-routing replay (medium, offline, deterministic).** For each merged PR in a repo's history, the reviewers who approved are a revealed-preference expert signal. Replay: at the PR's base commit, compute memoir's top-3 for the touched files (history truncated at that commit) and measure hit rate vs. actual approvers; compare against baselines "last committer" and "most commits ever". Needs PR metadata (GitHub API or a `Reviewed-by:` trailer corpus — Linux, Git, Valkey use trailers). Falsifies the premise if memoir does not beat "last committer" at predicting who reviewed.
3. **Bug-fix authorship replay (medium).** For each fix commit, who fixed the bug in file F? Check whether the fixer was in memoir's top-3 at the time of the fix. Same baselines. Measures "who ends up understanding the file", not "who claims to".
4. **Human survey (strong, expensive).** Ask active contributors of one repo "who would you ask about file F?" for ~50 files; compare lists. This is the only direct test of the thesis; the others are proxies.

What would falsify it: on (2) or (3), memoir ≤ last-committer baseline. Given section 1 (memoir ≈ recency on active files), the interesting test is on files whose last committer is a sweep/one-off: there the premise predicts memoir should beat last-touch clearly; if it does not, the extra machinery is not buying anything over `git log -1`.

Also proposed for direction (not implemented): surface raw alongside decayed (or a longer half-life) for legacy-modernization use; do not award `first_authored` to root/import/mass commits; cap the size term; report dormancy explicitly; an `identities` helper that suggests `.mailmap` lines for same-name/different-email authors.
