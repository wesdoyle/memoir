# Proposal: `memoir person <name-or-email> [--json]` — the reverse question

Status: proposal with prototype evidence (scratch script against the existing indexes; nothing in the package yet). If approved, the build happens on a new branch.

## 1. Shape of the answer: rollup, not list

For person P: every file at HEAD whose history contains a touch by P, P's rank in that file's `current` (decayed) and `built_it` (raw) rankings, then three aggregations:

1. **Top files** — the 8 highest-scoring files in each list (evidence: rank, score, commits, last touch). On a flat repository (Valkey: `src/*.c`) this *is* the territory; directories cannot say "cluster" or "acl" there.
2. **Directories** — for every ancestor level of every file: `files_in_dir` (at HEAD), `top3_current`, `top3_built_it`, `coverage = top3/files`, `Σscore` (current) and `Σraw` (built_it) over files where P is top-3. Ranked by **expertise mass** (`Σscore + Σraw`), not by file count or coverage — coverage alone promotes tiny directories and vendored dumps (Vadim "owns" 100% of `3rdparty/clapack`). Coverage is shown as information.
3. **Themes** — a few words per person, from path tokens (below).

Summary line: files with a record, top-3 current / built_it counts, last touch; both lists are always present and labeled, because the departed-founder case is exactly "built_it full, current empty" (antirez: 224 built_it vs 59 current, and the 59 are low-traffic files where nobody else is current either).

**Depth.** Compute all levels; keep a level when it is *concentrated*: drop a parent if one child holds ≥70% of its strong files (the child is the real unit), drop a child whose coverage is not ≥1.5× its parent's (the parent explains it). Present hierarchically: a kept parent with its kept children indented (Vadim: `modules` → `core/src` 116.8, `dnn/src/layers` 81.0, `imgproc` 50.9, `core/test` 31.1). Without a rule like this `src/` absorbs everything; with only "most specific" you get `utils/lru` (3 files, 100%) above `modules/core/src`.

**Vendored code is excluded by default** (`deps/`, `3rdparty/`, `third_party/`, `vendor/`, `external/`, `node_modules/`): importers are the "creator" of hundreds of files they never read. Before exclusion antirez's top themes were `jemalloc, deps, lua, msvc` and Vadim's `harfbuzz, rdparty, libjasper, clapack`; after, sentinel/replication/stream and core/imgproc/intrin. `--include-vendored` to see it.

## 2. Identity — now load-bearing

**Resolving the argument.** Exact email → that identity. Otherwise case-insensitive substring over names and emails; the hits are grouped by union-find over *shared key (email) or shared normalized name*; one group → use it, and if it spans several keys the report says so and prints the merge (`merged 3 identities: Madelyn Olson <gmail> (113), <noreply> (103), <amazon> (38). Add them to .mailmap to make it permanent.`); several groups → "ambiguous" with the candidates (`Viktor` → Viktor Szépe vs Viktor Söderqvist; retype the full name). The union over key *or* name is what makes `antirez` resolve to antirez/Salvatore Sanfilippo/antirez@metal.(none) as one person. This is a report-time merge; the index is unchanged.

**`memoir identities [--repo]` — the `.mailmap` suggestion helper.** Deterministic, read-only, emits a `.mailmap` block with a tier per line for you to review (nothing is written):
- `high`: same normalized multi-token name (≥2 tokens), different emails; canonical = most commits. Valkey 61, vscode 279, opencv 161 lines. Top: Benjamin Pasero ×3 (4,256 + 1,216 commits), Daniel Imms ×3, Joao Moreno, Matt Bierner, Alexander Alekhin ×3, Alexander Smorkalov ×4, Madelyn Olson ×3.
- `noreply`: `ID+login@users.noreply.github.com` whose login equals another identity's email local part or squashed name (`ranshid` → Ran Shidlansik <ranshid@amazon.com>, `Tyriar` → Daniel Imms, `lszomoru`, `justschen` → Justin Chen). Valkey 6, vscode 71, opencv 43.
- `names`: one email, several spellings (already one identity in memoir; this picks the canonical display name): antirez / Salvatore Sanfilippo, Alex Dima / Alexandru Dima, Megan Rogge / meganrogge, guybe7 / Guy Benoish.
Single-token names are never merged by name (too many "Alex"); placeholder emails and bots are skipped. Once you commit a `.mailmap`, `git log` applies it and the index rebuild picks it up.

## 3. Themes, deterministically

Tokenize each path (split on `/ _ - .` and camelCase, lowercase, drop the extension, digits, tokens < 3 chars and a stop list: `src main java org com test tests unit integration include lib h c cpp hpp ts py md ...`). `df(t)` = files at HEAD containing token t; `N` = files at HEAD. For P, `tf(t)` = Σ over P's strong files containing t of `max(score_current, raw_built_it) × log1p(n_authors)` — weighting by P's score and by how contested the file is, so that a directory of sole-author dumps cannot outvote one heavily-contested file P leads. `theme(t) = tf(t) × log(N / df(t))`, require ≥2 files, take the top 6. Two refinements still to do: drop tokens with `df/N > 0.2` (repo-name tokens: `opencv`, `valkey`) and treat the last path component's tokens slightly higher than directory tokens.

What it produces (Valkey, vendored excluded, weighted):

| person | themes | judgement |
|---|---|---|
| Madelyn Olson | cluster, crc, acl, scripting, auth, crcspeed | acl/auth/crc right; cluster from the cluster tests; `config` is in top files (#2 on config.c) but not a token theme because the path is just `config.c` (df=1 → tf=1) — one-file territories need the top-files list |
| Viktor Söderqvist | hashtable, valkey, moduleapi, support, cluster, module | hashtable (he wrote it), cluster, module right; `valkey`, `support` noise |
| Binbin | cluster, commands, moduleapi, sentinel, slot, command | right |
| antirez | type, sentinel, replication, stream, hyperloglog, rdb | right (`type` = tests/unit/type) |
| Josh Soref (noise control) | unit, type, rax, stream, cluster, bitops | the spelling sweep shows up as test-directory tokens; weak, as it should be |
| Vadim Pisarevsky (OpenCV) | opencv, imgproc, intrin, flann, layers, calib | imgproc/intrin/dnn-layers/calib right; `opencv` noise (IDF floor fixes it) |

Signal, with two fixable noise classes. It will never say "config" for a single file named `config.c`; that is what top files are for.

## 4. Cost, and materialization

Measured on the prototype (per-file `history` + `rank`, index path):

| person | candidate files at HEAD | per-file cost | total |
|---|---|---|---|
| Madelyn Olson (valkey) | 443 | 3.6 ms | 1.6 s |
| Viktor Söderqvist | 396 | 4.0 ms | 1.6 s |
| antirez | 634 | 2.1 ms | 1.3 s |
| Vadim Pisarevsky (opencv) | 1,405 | 1.0 ms | 1.4 s |
| Shay Banon (elasticsearch) | see below | 38 ms (ES files are deep) | — |

Two real costs, one bug-like finding:
- **Candidate discovery is wrong without forward lineage.** Shay's commits are recorded under pre-rename paths (`modules/elasticsearch/src/...`), so "files at HEAD with a record by P" must be computed through lineage: for each HEAD file, does its lineage contain one of P's commits? That is a lineage query per HEAD file (0.43 ms/file on ES; 2.1 s for the 4,946 files under `server/src/main/java/org/elasticsearch`, 1,041 of which have a Shay record — 21%) — or a materialized table.
- **Ranking every file is 1–4 ms/file**, so a prolific author on a big repo is seconds to tens of seconds, and `audit` pays the same per file.

Proposal: materialize at build time, in the index (schema v4):
- `file_lineage(path_at_head, pos)` — the commit positions in each HEAD file's history. Makes "files P touched" a join (instant), gives `audit` and `person` their candidate sets, and is what incremental update must maintain anyway (append for touched paths; rebuild rows for renamed/new paths).
- `file_rank(path, author_key, rank_current, score, rank_raw, raw_score)` for the top-5 of each list per file, computed with `now = build time` and the default `Weights`, both recorded in `meta`. Decay moves slowly relative to the update cadence (HL 18 months), so top-3 membership from a days-old `now` is stable; the report states `ranks as of <built_at>`; `--now` or non-default weights recompute live from `file_lineage` (seconds, not minutes). Incremental update recomputes `file_rank` only for paths touched by the new commits — but note that *decay alone* shifts every score; after a long gap (> ~1 month) a refresh should recompute all ranks (cheap: valkey 2 s, ES 43 s) — propose: recompute all when `now − built_at` > 30 days, else touched paths only.
- Build cost: +0.9 ms/file → valkey +2 s (on 7 s), opencv +7 s, flink +25 s, ES +43 s (on 82 s), vscode similar. `audit` then becomes a table scan.

Expected after: `person` = one join for candidates + one `file_rank` lookup per file (µs) + rollup arithmetic → well under a second for anyone, including Shay Banon on all of Elasticsearch. Before/after to be reported like the perf work.

## 5. Canary outputs (prototype, today)

- **Madelyn Olson** → top files current: MAINTAINERS.md, test_crc64combine.cpp, **config.c (#2)**, DEVELOPMENT_GUIDE.md, **acl.c (#1)**, GOVERNANCE.md, cluster_legacy.c (#3); themes acl/auth/crc/cluster. Known territory named. The governance docs at the top are honest (she wrote them) and are the kind of thing an agent should see before pulling her in.
- **Viktor Söderqvist** → hashtable.c #1, test_hashtable.cpp #1, module.c #2, **cluster.c #1**, server.c #2; themes hashtable/cluster/module. Named.
- **Vadim Pisarevsky** → `modules/core/src` Σ116.8 (ocl.cpp, mathfuncs_core, umatrix, matrix.cpp all #1), `dnn/src/layers`, `imgproc`, `core/test`; themes imgproc/intrin/flann/layers/calib. Named.
- **antirez** → `current`: 59 weak files (psync2.tcl #3 at 0.4, lolwut.c) — correctly "not current"; `built_it`: cluster.c #1 raw 10.1, server.c, hyperloglog.c, sentinel.c, server.h, networking.c, replication.c, t_stream.c — the founder under built_it, as required.

## 6. Decision points for the gate

1. Build it (on a new branch): `memoir person` + `memoir identities`, `file_lineage` + `file_rank` materialization (schema v4), incremental maintenance, tests on the fixture (Alice → src/core.py territory; Bob → helpers via the rename; Carol's sweep weak), perf before/after, canary outputs for the four people above in the report.
2. Keep vendored exclusion on by default? (Recommended yes.)
3. `now` policy for materialized ranks: recompute touched paths on every update, everything when older than 30 days. (Recommended.)
4. Theme noise: IDF floor (`df/N > 0.2` dropped) and basename weighting. (Recommended; small.)
