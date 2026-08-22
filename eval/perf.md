# Performance baseline (v0, 2026-08-21)

Measurement only. No caching, no persistence, no optimizations. Reproduce with `eval/bench.py` (see its docstring); the git subprocess time is attributed by wrapping `memoir.mining._git` from the bench, not by instrumenting the package.

Machine: Apple M4 Pro, 12 cores, 48 GB. git 2.39.5 (Apple Git-154), Python 3.12.4, uv 0.8.4. Repos are full-history `--no-checkout --single-branch` clones under `eval/repos/`; pack sizes: vscode 1.24 GiB (163,752 commits), elasticsearch 1.24 GiB (104,744), flink (38,347), opencv (37,642), valkey 147 MiB (14,019). Wall clock, median of 3 unless stated; run uncontended.

## 1. Where the time goes: one `memoir who` (`mine_file` + `rank`)

Light / medium / heavy-history file per repo. `git log` = the single `git log --follow --numstat` call; `parse+facts` = Python record parsing and aggregation; `score` = the v0 formula over all authors.

| repo | file | commits | authors | total ms | git log | check-mailmap | parse+facts | score | git % |
|---|---|---|---|---|---|---|---|---|---|
| valkey | `lzf_c.c` | 6 | 4 | 146 | 146 | 0 | 0 | 0.0 | 100% |
| valkey | `t_zset.c` | 290 | 85 | 279 | 254 | 9 | 16 | 0.2 | 94% |
| valkey | `server.c` | 1726 | 280 | 1349 | 1069 | 11 | 269 | 0.6 | 80% |
| opencv | `has_non_zero.simd.hpp` | 5 | 5 | 385 | 384 | 0 | 1 | 0.0 | 100% |
| opencv | `imgwarp.cpp` | 283 | 78 | 436 | 411 | 10 | 15 | 0.2 | 97% |
| opencv | `matrix.cpp` | 291 | 59 | 383 | 372 | 0 | 11 | 0.1 | 97% |
| flink | `JobMasterId.java` | 30 | 12 | 664 | 664 | 0 | 1 | 0.0 | 100% |
| flink | `JobMaster.java` | 270 | 60 | 651 | 640 | 0 | 11 | 0.1 | 98% |
| flink | `ExecutionGraph.java` | 420 | 69 | 556 | 523 | 13 | 20 | 0.2 | 96% |
| elasticsearch | `EngineException.java` | 13 | 6 | 1465 | 1464 | 0 | 0 | 0.0 | 100% |
| elasticsearch | `IndexMetadata.java` | 395 | 88 | 1679 | 1642 | 13 | 24 | 0.2 | 99% |
| elasticsearch | `InternalEngine.java` | 875 | 88 | 1746 | 1702 | 10 | 34 | 0.2 | 98% |
| vscode | `lazy.ts` | 6 | 3 | 1817 | 1817 | 0 | 0 | 0.0 | 100% |
| vscode | `textModel.ts` | 402 | 38 | 2017 | 1995 | 11 | 11 | 0.1 | 99% |
| vscode | `extHost.api.impl.ts` | 1837 | 123 | 2586 | 2428 | 11 | 147 | 0.3 | 94% |

Findings:
- **The git subprocess is 80–100% of the cost.** Python parse+facts is ≈0.1–0.15 ms per commit (269 ms for 1,726 commits; 147 ms for 1,837); scoring is sub-millisecond. `check-mailmap` is one ≈10 ms call when there are co-author trailers, 0 otherwise.
- **`git log --follow` cost is set by the repository's history, not the file's.** A 6-commit file costs 1.8 s in vscode and 0.15 s in valkey; within a repo, light and heavy files are within ~1.5× of each other (vscode 1.8–2.6 s; elasticsearch 1.5–1.7 s; flink 0.56–0.66 s). `--follow` walks every commit, running rename detection at each tree that touches the path's directory.
- Memory follows the same rule (peak RSS of the git process, `/usr/bin/time -l`): vscode `lazy.ts` 612 MB, vscode `extHost.api.impl.ts` 650 MB, valkey `server.c` 316 MB. The Python process itself is ~85 MB.

## 2. Git-level micro-benchmarks

Same files; each variant is a separate process, median of 3. Isolates `--follow` and `--numstat` (diff) cost from the commit walk.

| repo | file | commits | log --follow --numstat | log --numstat (no follow) | log --follow (no numstat) | log (plain) | rev-list --count |
|---|---|---|---|---|---|---|---|
| valkey | `lzf_c.c` | 5 | 147 | 119 | 142 | 118 | 122 |
| valkey | `t_zset.c` | 297 | 259 | 225 | 167 | 143 | 136 |
| valkey | `server.c` | 1212 | 1029 | 793 | 183 | 149 | 139 |
| opencv | `has_non_zero.simd.hpp` | 4 | 374 | 132 | 404 | 126 | 139 |
| opencv | `imgwarp.cpp` | 331 | 422 | 304 | 289 | 175 | 171 |
| opencv | `matrix.cpp` | 329 | 381 | 281 | 273 | 179 | 171 |
| flink | `JobMasterId.java` | 4 | 653 | 415 | 675 | 412 | 428 |
| flink | `JobMaster.java` | 266 | 656 | 506 | 667 | 409 | 404 |
| flink | `ExecutionGraph.java` | 308 | 545 | 468 | 461 | 407 | 394 |
| elasticsearch | `EngineException.java` | 4 | 1416 | 871 | 1409 | 863 | 863 |
| elasticsearch | `IndexMetadata.java` | 177 | 1633 | 871 | 1542 | 781 | 787 |
| elasticsearch | `InternalEngine.java` | 367 | 1704 | 1072 | 1472 | 935 | 911 |
| vscode | `lazy.ts` | 6 | 1806 | 1031 | 1768 | 1043 | 1012 |
| vscode | `textModel.ts` | 485 | 1931 | 1476 | 1904 | 1275 | 1238 |
| vscode | `extHost.api.impl.ts` | 1247 | 2351 | 1557 | 2056 | 1298 | 1304 |

(`commits` here is `rev-list --count -- path` without `--follow`, hence lower than section 1 for renamed files.)

Findings:
- **The floor is the commit walk itself.** `rev-list --count -- path` — no diff output at all — costs 0.12 s (valkey) to 1.0–1.3 s (vscode). Every path-limited `git log` visits every commit reachable from HEAD; the pathspec filters what is printed, not what is walked.
- **`--follow` roughly doubles the cost on shallow-history files** (vscode `lazy.ts` 1.0 → 1.8 s; elasticsearch `EngineException.java` 0.87 → 1.42 s) because it forces rename detection at every commit and disables history simplification. `--numstat` adds the diff cost on the commits that are printed, visible only on deep-history files (`server.c` 183 → 1029 ms).
- A 4-commit file and a 300-commit file in the same repo cost within 1.5× of each other. File history depth is a second-order effect; repository history depth is first-order.

## 3. Directory throughput (`memoir audit` inner loop)

Sequential `mine_file` + `rank` over every file in the directory; per-file distribution and cost by history depth.

### valkey `src` — 738 files, wall 122.0 s, 6.0 files/s
- per file: min 112 ms · p50 150 · p90 193 · p95 206 · max 1322 · mean 165
- by history depth: 0-5 commits: n=157, median 159 ms; 5-20 commits: n=467, median 147 ms; 20-100 commits: n=73, median 170 ms; 100-500 commits: n=32, median 206 ms; 500-∞ commits: n=9, median 555 ms
- slowest: 1322 ms (1726 commits, 280 authors); 998 ms (811 commits, 155 authors); 929 ms (1613 commits, 251 authors)

Per-file cost is flat at ~150 ms until history exceeds a few hundred commits. Distributions for the larger repos were not run (direction: do not benchmark the largest repos); from section 1, expect p50 ≈ 0.4 s (opencv), 0.65 s (flink), 1.5 s (elasticsearch), 1.9 s (vscode), i.e. the 10 P4 audits cost 1–15 min each.

### The alternative, measured once: a single whole-repo walk

`git log --numstat -M --format=<header>` over all of Valkey (14,019 commits): **6.8 s**, 6.8 MB of output, every commit × every path including rename records. Scoped to `src/`: 5.5 s. Against 122 s for 738 per-file `--follow` walks that is ~18–22×, and the gap widens with file count (a 10k-file audit of vscode per-file is ~5 h; one walk is a minute or two).

## 4. Process startup

| command | median ms (of 5) |
|---|---|
| `uv run memoir --help` | 86 |
| `.venv/bin/memoir --help` | 71 |
| `python -c 'import memoir.cli'` | 38 |
| `python -c 'import memoir.mining'` | 25 |
| `git --version` | 9 |

Startup is noise next to a single `git log` on any repo larger than the fixture. typer/fastmcp imports cost ≈13 ms over the mining module alone.

## 5. Baseline summary and proposed optimizations (not implemented)

**Baseline: `who` ≈ one `git log --follow --numstat` ≈ 0.15 s (14k-commit repo) to 2.5 s (164k-commit repo), nearly independent of the file; `audit` ≈ files × that (6 files/s on valkey).** The git walk is 80–100% of every number above; Python parsing is 0.1–0.15 ms/commit and scoring is sub-millisecond. Everything below attacks the walk; nothing else is worth touching until it is.

1. **One walk, all files.** Replace per-file `--follow` with a single streamed `git log --numstat -M --format=…` (optionally pathspec-scoped), parsed incrementally into per-path facts; rename lineage reconstructed from the `{old => new}` numstat records in the same stream. Measured 18–22× on valkey `src`; larger on larger repos. Same facts, same determinism; the fixture's rename/bot/co-author/merge tests are the acceptance test. Caveat: `-M` and `--follow` both default to 50% similarity, but `--follow` can find renames that whole-tree `-M` misses when a commit has many candidate files — expect rare lineage differences; measure on the P4 directories.
2. **Persist the walk as an index** (constraint relaxed 2026-08-21 by direction). The single walk's output, aggregated to per-(path, author) facts plus per-path lineage and last commit, keyed by the repo's HEAD; `who`/`audit`/MCP then query it. The metric is query time: today 0.15–2.5 s per `who`; from an index it should be milliseconds. Build cost is the one walk. Staleness must be explicit (HEAD recorded; rebuild when it moves; incremental update is a follow-on).
3. **Parallelize the per-file loop** (12 cores, ~8× wall on audits, no result change). Cheap and orthogonal, but superseded by (1) on anything but small repos.
4. **Per-file fast path without `--follow`.** `git log -- path` is ~half the cost of `--follow` on shallow files; a manual rename chase at the file's first commit would recover lineage. Only worth it if (1)/(2) are rejected.
5. **Parse cost** (0.1–0.15 ms/commit) matters only on >1k-commit files and only after the walk is fixed.
6. **git's own index.** `git commit-graph write --changed-paths` (bloom filters) speeds path-limited walks without `--follow`; it is git-side state inside `.git`, not memoir persistence, and does not help `--follow`. Note for completeness.

## 6. After P5: single walk + persisted index (measured 2026-08-21)

Same machine. `eval/bench.py build|query|equiv`; query and equivalence use `random.Random(42).sample` of 100 files from `git ls-tree -r HEAD`. Largest repos (elasticsearch, vscode) not run by direction.

### Build: one `git log --numstat -M` walk, persisted to SQLite

| repo | commits | (commit, path) rows | distinct paths | build time | index size |
|---|---|---|---|---|---|
| valkey | 14,019 | 35,603 | 3,132 | 6.9 s | 3.7 MB |
| opencv | 37,642 | 122,969 | 19,382 | 18.1 s | 17.7 MB |
| flink | 38,347 | 350,015 | 71,154 | 23.9 s | 87.3 MB |

Build time ≈ the raw git walk (valkey 6.8 s raw → 6.9 s; flink 21.8 s raw → 23.9 s): parsing and SQLite insertion add <10%. Cost is one walk per HEAD, equal to roughly 45 (valkey) to 40 (flink) per-file `--follow` calls.

### Query: `who` on 100 seeded files, live vs index

"cold" opens the SQLite file per query (what one CLI invocation does); "warm" reuses one connection (what `audit` and an MCP server do). Process startup (~70–90 ms, §4) is excluded from all three and now dominates a cold CLI `who`.

| repo | live (`--follow` per file) | index, cold | index, warm | median speedup | 100 files total |
|---|---|---|---|---|---|
| valkey | mean 126 · median 114 · p95 188 · stdev 33 · min 87 · max 234 ms | mean 0.40 · median 0.15 · p95 1.82 · stdev 0.93 · min 0.09 · max 7.98 ms | mean 0.29 · median 0.05 · p95 1.68 · stdev 0.91 · min 0.01 · max 7.79 ms | 742× | 12.6 s → 0.04 s |
| opencv | mean 298 · median 287 · p95 419 · stdev 63 · min 209 · max 563 ms | mean 0.35 · median 0.15 · p95 1.46 · stdev 0.80 · min 0.10 · max 7.05 ms | mean 0.23 · median 0.05 · p95 1.23 · stdev 0.78 · min 0.01 · max 6.73 ms | 1,882× | 29.8 s → 0.03 s |
| flink | mean 581 · median 541 · p95 876 · stdev 174 · min 353 · max 1,378 ms | mean 0.24 · median 0.15 · p95 0.74 · stdev 0.27 · min 0.12 · max 2.46 ms | mean 0.13 · median 0.05 · p95 0.57 · stdev 0.25 · min 0.03 · max 2.24 ms | 3,567× | 58.1 s → 0.02 s |

Index query cost is flat across repos (median 0.15 ms cold, 0.05 ms warm) and set by the file's own record count (max 8 ms for the 1,700-commit files), i.e. the shape the per-file design lacked: cost now tracks the file, not the repository. `audit` of valkey `src` goes from 122 s live to the index build (6.9 s) plus well under a second of queries; repeated audits are free until HEAD moves.

### Equivalence: walk/index lineage vs per-file `--follow`, same 100 files

| repo | files differing | top-1 changed | explanation |
|---|---|---|---|
| valkey | 5 | 3 | 3 copies followed by `--follow` (source still at HEAD: `sentinel-masters → -primaries`, `hsetex → msetex`, `client-setname → client-capa`); 1 `--follow` chain (`propagate.c ← … ← zmalloc.h`); 1 rename-away counted by `--follow` as a 114-line deletion (`Makefile`) |
| opencv | 11 | 2 | mostly copies (`libjpeg → libjpeg-turbo`, Android sample `strings.xml` across tutorials, images duplicated under `doc/`); 1 file where the walk found *more* (`ts.hpp`: 35 commits `--follow` lost through a bad rename hop) |
| flink | 52 | 23 | 38 copies (per-version test-resource fixtures, copied components), 12 `--follow` chains through boilerplate-similar unrelated files (`HadoopDummyProgressable → JobCancellationException`, `DummyCoGroupStub → CoGroupOperatorBase`), 1 true rename the whole-tree `-M` paired differently (`LongArraySerializerTest → ShortPrimitiveArraySerializerTest`), 1 path-order only |

Not the rename limit: `git log` emitted no "rename detection was skipped" warnings on flink, and `-M -l0` produced byte-identical output at the same cost. The differences are `--follow`'s semantics: it follows copies (the source need not be deleted) and, evaluating one path at a time, accepts similarity matches that whole-tree `-M` pairs elsewhere. The walk's lineage is the stricter one; it is now the reference and `mine_file` (`--follow`) is the live fallback. Adding `-C` (copies) to the walk is an open choice, not taken.

### Against the §5 proposals

1 (one walk) and 2 (persisted index) are done; 3 (parallel per-file loop) and 4 (`--follow`-free per-file path) are superseded for any repo worth indexing; 5 (parse cost) is visible only in build time and is <10% of it. Next cost centre is the build itself (one full walk per HEAD); incremental update (`old_head..HEAD`, re-resolving lineage for touched paths) is the obvious follow-on, and cold CLI startup (~80 ms) is now the floor for single `who` calls.

## 7. Incremental index update (2026-08-22)

`update_index()` walks only `old_head..HEAD` and prepends the new commits (positions below the current minimum; `pos` is an ordering key). Measured by building at `HEAD~N`, then updating to the tip (no-checkout clones, HEAD moved with `update-ref`):

| repo | full build at HEAD~N | N new commits | incremental update | speedup |
|---|---|---|---|---|
| valkey | 7.3 s | 30 | 0.13 s | 56× |
| valkey | 6.9 s | 300 | 0.39 s | 18× |
| flink | 25.0 s | 300 | 0.34 s | 74× |

Update cost is proportional to the new commits plus a constant (~0.1 s: `merge-base --is-ancestor`, `rev-list --count`, one `check-mailmap`), not to repository size. The result is identical to a full rebuild on every fixture file (test), including a rename, a merge, a co-author and a sweep crossing the update boundary. A HEAD that is not a descendant of the indexed commit (rebase, amend) falls back to a full rebuild.

## 8. `memoir person` and index v4 (2026-08-22, branch `person`)

Materializing `file_lineage` and per-file top-5 ranks at build time costs +7 s (valkey) to +23 s (elasticsearch) on the build (measured with all five builds concurrent) and roughly doubles index size. `memoir person` then answers in 0.17–0.28 s for Valkey/OpenCV authors and 1.4 s for Shay Banon across 1,488 Elasticsearch files (the per-file author-count query for theme weighting dominates), versus 1.3–1.6 s per person on the prototype's per-file live path — which could not even find Shay's files without lineage. See eval/person.md §7.

