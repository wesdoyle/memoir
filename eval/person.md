# Proposal: `memoir person <name-or-email> [--json]` — the reverse question

Status: built on branch `person` (2026-08-22). §§1–6 are the proposal as approved; §7 has what was built and measured.

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

## 7. Built (branch `person`)

- Index schema v4: `file_lineage(path, pos)` for every HEAD file and `file_rank` (top-5 current + top-5 raw per file) computed at `rank_now` with `rank_weights`; incremental update recomputes touched/new/renamed paths and prunes gone ones; all ranks recomputed when `rank_now` is >30 days old (`reranked`). Tests: materialized == live `rank()` on every fixture file; incremental == full rebuild (lineage by sha, ranks); stale rerank.
- `memoir person <name-or-email> [--json] [--include-vendored] [--top N] [--now]`, `memoir identities`.
- Changes from the proposal after measurement: basename-over-directory token weighting made themes worse (module identity lives in directory tokens: `imgproc`, `cluster`) — reverted to equal weights; the repository's own name is stop-listed instead of relying on the IDF floor (kept at 0.2; 0.1 dropped `cluster` on Valkey); the contested-file weight needs an author count, which the materialized path gets from `file_lineage`; with split identities the strongest row per file is taken (the `.mailmap` is the real fix).

### Cost, before / after

| person | files | before (prototype: per-file live rank, current-name candidates) | after (`memoir person`, end-to-end incl. startup) |
|---|---|---|---|
| Madelyn Olson (valkey) | 426 | 1.6 s | 0.22 s |
| Viktor Söderqvist (valkey) | 398 | 1.6 s | 0.19 s |
| antirez (valkey) | 265 | 1.3 s | 0.17 s |
| Vadim Pisarevsky (opencv) | 1,201 | 1.4 s | 0.28 s |
| Shay Banon (elasticsearch) | 1,488 | not feasible: 11 files found by current-name match; ≈60 s by per-file rank once found via lineage | 1.4 s |

Build cost of materialization (v3 → v4, all five built concurrently so contended): valkey 6.9 → 13.9 s (3.7 → 7.8 MB), opencv 18.1 → 29.2 s (32 MB), flink 23.9 → 42.5 s (161 MB), elasticsearch 82.5 → 105 s (386 MB), vscode 79.9 → 98 s (192 MB). `who`/`audit` rankings are unchanged (regress `v4` vs `fixes`: no movement).

### Canaries (actual output, `--top 6`)

```
Madelyn Olson — keys: 34459052+madolson@users.noreply.github.com, madelyneolson@gmail.com, matolson@amazon.com
  note: merged 3 identities for this report: Madelyn Olson <madelyneolson@gmail.com> (113), Madelyn Olson <34459052+madolson@users.noreply.github.com> (103), Madelyn Olso
  files touched (at HEAD): 426; top-3 current: 139; top-3 built_it: 111; last touch 2026-08-13; ranks as of 2026-08-22; vendored excluded
  themes: cluster, scripting, crc, server, acl, auth
  current — can answer today:
    MAINTAINERS.md  #1 cur 6.11 · #1 raw 6.70
    src/unit/test_crc64combine.cpp  #1 cur 5.25 · #1 raw 6.57
    src/config.c  #2 cur 4.99 · #3 raw 5.06
    DEVELOPMENT_GUIDE.md  #1 cur 4.42 · #1 raw 5.86
    src/acl.c  #1 cur 4.40 · #2 raw 4.46
    GOVERNANCE.md  #1 cur 4.29 · #1 raw 5.91
  built_it — built it (undecayed):
    MAINTAINERS.md  #1 cur 6.11 · #1 raw 6.70
    tests/unit/cluster/hostnames.tcl  #1 cur 1.54 · #1 raw 6.66
    src/unit/test_crc64combine.cpp  #1 cur 5.25 · #1 raw 6.57
    src/lolwut9.c  #1 cur 3.92 · #1 raw 5.93
    GOVERNANCE.md  #1 cur 4.29 · #1 raw 5.91
    DEVELOPMENT_GUIDE.md  #1 cur 4.42 · #1 raw 5.86
  directories (by expertise mass; top-3 current / built_it of files):
    src/  86/738 (12%) · 65/738 (9%)  mass 215.4  e.g. test_crc64combine.cpp, config.c, lolwut9.c
    tests/  37/344 (11%) · 32/344 (9%)  mass 126.8  e.g. hostnames.tcl, crash.c, crash.tcl
    utils/  4/37 (11%) · 4/37 (11%)  mass 7.9  e.g. generate-module-api-doc.rb, gen-test-certs.sh, redis-sha1.rb
    .github/workflows/  2/20 (10%) · 2/20 (10%)  mass 6.0  e.g. ci.yml, coverity.yml
```

```
Viktor Söderqvist — keys: viktor.soderqvist@est.tech, viktor@zuiderkwast.se
  note: merged 2 identities for this report: Viktor Söderqvist <viktor.soderqvist@est.tech> (174), Viktor Söderqvist <viktor@zuiderkwast.se> (3). Add them to .mailmap to 
  files touched (at HEAD): 398; top-3 current: 204; top-3 built_it: 168; last touch 2026-06-16; ranks as of 2026-08-22; vendored excluded
  themes: hashtable, support, cluster, server, moduleapi, modules
  current — can answer today:
    src/hashtable.c  #1 cur 7.25 · #1 raw 7.89
    src/unit/test_hashtable.cpp  #1 cur 6.92 · #1 raw 7.77
    src/module.c  #2 cur 6.43 · #3 raw 6.51
    src/cluster.c  #1 cur 6.11 · #2 raw 6.19
    src/fmtargs.h  #1 cur 5.99 · #1 raw 6.52
    src/server.c  #2 cur 5.84 · #3 raw 5.92
  built_it — built it (undecayed):
    src/hashtable.c  #1 cur 7.25 · #1 raw 7.89
    src/unit/test_hashtable.cpp  #1 cur 6.92 · #1 raw 7.77
    src/hashtable.h  #1 cur 5.64 · #1 raw 6.75
    tests/integration/cross-version-replication.tcl  #1 cur 4.90 · #1 raw 6.70
    utils/module-api-since.rb  #1 cur 2.25 · #1 raw 6.55
    tests/modules/stream.c  #2 cur 0.73 · #1 raw 6.53
  directories (by expertise mass; top-3 current / built_it of files):
    src/  101/738 (14%) · 83/738 (11%)  mass 344.4  e.g. hashtable.c, test_hashtable.cpp, module.c
    tests/  79/344 (23%) · 60/344 (17%)  mass 305.8  e.g. cross-version-replication.tcl, stacktrace.tcl, stream.tcl
    LICENSES/  8/8 (100%) · 8/8 (100%)  mass 71.4  e.g. CC0-1.0.txt, Apache-2.0.txt, MIT.txt
    tests/support/  8/13 (62%) · 5/13 (38%)  mass 39.4  e.g. stacktrace.tcl, server.tcl, cluster_util.tcl
    utils/  3/37 (8%) · 3/37 (8%)  mass 23.4  e.g. module-api-since.rb, generate-module-api-doc.rb, generate-fmtargs.py
    .github/ISSUE_TEMPLATE/  2/5 (40%) · 4/5 (80%)  mass 13.9  e.g. crash_report.yml, config.yml, bug_report.md
    src/modules/lua/  2/13 (15%) · 2/13 (15%)  mass 5.5  e.g. script_lua.c, debug_lua.h
```

```
antirez — keys: antirez@gmail.com, name:antirez
  note: merged 2 identities for this report: antirez <antirez@gmail.com> (5999), Salvatore Sanfilippo <antirez@gmail.com> (1038), antirez <antirez@metal.(none)> (25). Add
  files touched (at HEAD): 265; top-3 current: 63; top-3 built_it: 247; last touch 2020-06-25; ranks as of 2026-08-22; vendored excluded
  themes: type, cluster, server, sentinel, replication, stream
  current — can answer today:
    tests/integration/psync2.tcl  #3 cur 0.41 · #1 raw 7.36
    tests/unit/bitfield.tcl  #2 cur 0.35 · #1 raw 6.81
    src/lolwut.c  #3 cur 0.34 · #1 raw 8.16
    utils/create-cluster/create-cluster  #3 cur 0.34 · #1 raw 6.21
    src/lolwut6.c  #3 cur 0.30 · #1 raw 6.97
    tests/integration/psync2-pingoff.tcl  #3 cur 0.30 · #1 raw 5.28
  built_it — built it (undecayed):
    src/cluster.c  #- cur 0.59 · #1 raw 10.11
    src/server.c  #- cur 0.56 · #1 raw 9.82
    src/cluster_legacy.c  #- cur 0.56 · #1 raw 9.67
    src/hyperloglog.c  #- cur 0.51 · #1 raw 9.49
    src/sentinel.c  #- cur 0.50 · #1 raw 9.44
    src/eval.c  #- cur 0.45 · #1 raw 9.33
  directories (by expertise mass; top-3 current / built_it of files):
    src/  27/738 (4%) · 132/738 (18%)  mass 790.9  e.g. cluster.c, server.c, cluster_legacy.c
    tests/  17/344 (5%) · 82/344 (24%)  mass 405.3  e.g. psync2.tcl, bitfield.tcl, scripting.tcl
    utils/  19/37 (51%) · 23/37 (62%)  mass 134.1  e.g. test-lru.rb, hll-gnuplot-graph.rb, hll-err.rb
    tests/integration/  4/38 (10%) · 13/38 (34%)  mass 66.9  e.g. psync2.tcl, replication-psync.tcl, replication-3.tcl
    src/modules/  4/24 (17%) · 9/24 (38%)  mass 56.0  e.g. helloworld.c, hellotype.c, Makefile
    tests/unit/type/  1/10 (10%) · 10/10 (100%)  mass 46.3  e.g. stream.tcl, list-3.tcl, stream-cgroups.tcl
    utils/lru/  3/3 (100%) · 3/3 (100%)  mass 19.7  e.g. test-lru.rb, lfu-simulation.c, README
```

```
Vadim Pisarevsky — keys: name:vadim pisarevsky, vadim.pisarevsky@gmail.com, vadim.pisarevsky@itseez.com, vadim.pisarevsky@me.com
  note: merged 4 identities for this report: Vadim Pisarevsky <vadim.pisarevsky@gmail.com> (2243), Vadim Pisarevsky <no@email> (953), Vadim Pisarevsky <vadim.pisarevsky@i
  files touched (at HEAD): 1201; top-3 current: 518; top-3 built_it: 615; last touch 2026-07-17; ranks as of 2026-08-22; vendored excluded
  themes: imgproc, geometry, intrin, data, simd, layers
  current — can answer today:
    modules/core/src/ocl.cpp  #1 cur 9.07 · #1 raw 9.50
    modules/core/include/opencv2/core/hal/intrin_neon.hpp  #1 cur 8.07 · #1 raw 8.45
    modules/core/src/mathfuncs_core.simd.hpp  #1 cur 7.69 · #1 raw 8.05
    modules/core/src/umatrix.cpp  #1 cur 6.65 · #1 raw 8.17
    modules/core/src/matrix.cpp  #1 cur 5.36 · #1 raw 6.58
    modules/imgproc/src/opencl/remap.cl  #1 cur 5.33 · #1 raw 5.91
  built_it — built it (undecayed):
    modules/core/src/ocl.cpp  #1 cur 9.07 · #1 raw 9.50
    modules/core/include/opencv2/core/hal/intrin.hpp  #1 cur 3.88 · #1 raw 9.10
    modules/core/include/opencv2/core/hal/intrin_neon.hpp  #1 cur 8.07 · #1 raw 8.45
    modules/core/src/umatrix.cpp  #1 cur 6.65 · #1 raw 8.17
    modules/core/src/mathfuncs_core.simd.hpp  #1 cur 7.69 · #1 raw 8.05
    modules/core/include/opencv2/core/hal/intrin_sse.hpp  #1 cur 3.34 · #1 raw 8.00
  directories (by expertise mass; top-3 current / built_it of files):
    modules/  407/2885 (14%) · 482/2885 (17%)  mass 1955.8  e.g. ocl.cpp, intrin_neon.hpp, mathfuncs_core.simd.hpp
    modules/imgproc/  72/299 (24%) · 95/299 (32%)  mass 387.3  e.g. remap.cl, imgwarp.cpp, drawing_text.cpp
    modules/core/src/  54/191 (28%) · 55/191 (29%)  mass 328.1  e.g. ocl.cpp, mathfuncs_core.simd.hpp, umatrix.cpp
    samples/  70/1167 (6%) · 85/1167 (7%)  mass 269.6  e.g. select3dobj.cpp, calibration.cpp, 3calibration.cpp
    modules/dnn/src/layers/  47/156 (30%) · 39/156 (25%)  mass 209.5  e.g. conv2_depthwise.simd.hpp, avgpool_layer.cpp, maxpool_layer.cpp
    samples/data/  44/122 (36%) · 44/122 (36%)  mass 132.6  e.g. stereo_calib.xml, letter-recognition.data, intrinsics.yml
    modules/geometry/  33/135 (24%) · 41/135 (30%)  mass 122.2  e.g. moments.cl, ptsetreg.cpp, test_filter_homography_decomp.cpp
```

```
Shay Banon — keys: kimchy@gmail.com
  files touched (at HEAD): 1488; top-3 current: 286; top-3 built_it: 1188; last touch 2015-07-24; ranks as of 2026-08-22; vendored excluded
  themes: index, action, cluster, admin, indices, routing
  current — can answer today:
    server/src/main/java/org/elasticsearch/action/admin/indices/flush/FlushRequestBuilder.java  #2 cur 0.03 · #1 raw 6.45
    server/src/main/java/org/elasticsearch/action/admin/indices/cache/clear/ClearIndicesCacheRequestBuilder.java  #2 cur 0.03 · #1 raw 6.40
    server/src/main/java/org/elasticsearch/action/admin/indices/refresh/RefreshRequestBuilder.java  #2 cur 0.03 · #1 raw 6.31
    server/src/main/java/org/elasticsearch/action/admin/indices/mapping/put/PutMappingRequestBuilder.java  #3 cur 0.03 · #1 raw 6.28
    server/src/main/java/org/elasticsearch/action/admin/indices/delete/DeleteIndexRequestBuilder.java  #2 cur 0.03 · #1 raw 6.09
    server/src/main/java/org/elasticsearch/rest/action/admin/indices/RestFlushAction.java  #2 cur 0.03 · #1 raw 6.03
  built_it — built it (undecayed):
    server/src/main/java/org/elasticsearch/gateway/GatewayService.java  #- cur 0.03 · #1 raw 8.03
    server/src/main/java/org/elasticsearch/gateway/GatewayAllocator.java  #- cur 0.05 · #1 raw 8.02
    LICENSE.txt  #5 cur 0.01 · #1 raw 7.69
    server/src/main/java/org/elasticsearch/index/mapper/ObjectMapper.java  #- cur 0.03 · #1 raw 7.66
    server/src/main/java/org/elasticsearch/rest/action/admin/cluster/RestClusterStateAction.java  #- cur 0.04 · #1 raw 7.64
    server/src/main/java/org/elasticsearch/monitor/jvm/JvmStats.java  #4 cur 0.04 · #1 raw 7.64
  directories (by expertise mass; top-3 current / built_it of files):
    server/src/main/java/org/elasticsearch/  246/4946 (5%) · 884/4946 (18%)  mass 4060.3  e.g. GatewayService.java, GatewayAllocator.java, ObjectMapper.java
    server/src/main/java/org/elasticsearch/injection/guice/  67/111 (60%) · 111/111 (100%)  mass 405.6  e.g. InheritingState.java, InternalFactory.java, FailableCache.jav
    server/src/test/java/org/elasticsearch/  5/2811 (0%) · 80/2811 (3%)  mass 394.8  e.g. FailedShardsRoutingTests.java, UpdateNumberOfReplicasTests.java, PrimaryElection
    modules/analysis-common/src/main/java/org/elasticsearch/analysis/common/  5/137 (4%) · 75/137 (55%)  mass 320.7  e.g. CzechAnalyzerProvider.java, BrazilianAnalyzerPro
    server/src/internalClusterTest/java/org/elasticsearch/  1/552 (0%) · 54/552 (10%)  mass 266.1  e.g. TransportTwoNodesSearchIT.java, DocumentActionsIT.java, IndexLifec
    server/src/main/java/org/elasticsearch/index/query/  1/99 (1%) · 33/99 (33%)  mass 130.6  e.g. QueryParsers.java, QueryBuilders.java, ParsedQuery.java
    server/src/main/java/org/elasticsearch/transport/  12/93 (13%) · 27/93 (29%)  mass 115.8  e.g. TransportRequestOptions.java, TransportService.java, SendRequestTranspo
    server/src/main/java/org/elasticsearch/rest/action/admin/indices/  4/47 (8%) · 20/47 (43%)  mass 104.6  e.g. RestIndicesStatsAction.java, RestDeleteIndexAction.java, 
```

