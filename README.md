# memoir

memoir is a prototype codebase expert-identifier. It mines git history deterministically to find the people most likely to hold the mental model of a file, and serves that answer to humans (CLI) and, later, to agents (MCP).

Last-touch attribution — the blame gutter, `git log -1` — often masks long-term authors behind lint sweeps, renames, and bot commits. As agents do more engineering work in legacy codebases, "which human should be pulled into this conversation" becomes routing infrastructure: an escalation path, a decision gate, a source of hidden context. memoir is a first pass at that answer.

## Quickstart

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/). No network access, no LLM calls; git is read through plumbing commands only. The only state memoir writes is the optional index under `.git/memoir/`.

```sh
git clone <this repo> memoir && cd memoir
uv sync
uv run pytest            # tests against a synthetic fixture repo
uv run memoir --help
```

## Usage

Run inside any git repository (or point at one with `--repo`).

**Who knows a file?**

```sh
$ uv run memoir who src/server.c -n 3
src/server.c — 1726 knowledge-bearing commits, 280 authors, formerly src/redis.c
  1. Binbin <…>            score 6.63 (raw 6.72)  85 commits · 12 co-authored · 1239 lines · last 2026-08-11 (0 mo ago) · 6 by others since
  2. Viktor Söderqvist <…> score 6.10 (raw 6.17)  23 commits · 32 co-authored · 1772 lines · last 2026-08-11 (0 mo ago) · 5 by others since
  3. Ran Shidlansik <…>    score 3.95 (raw 4.00)  10 commits · 7 co-authored · 262 lines · last 2026-08-11 (0 mo ago) · 7 by others since
  by raw score (before time decay): antirez 9.88 (last 2020-06-10) · Binbin 6.72 (last 2026-08-11) · Viktor Söderqvist 6.17 (last 2026-08-11)
  last commit: Satheesha CH Gowda 2026-08-14 (rank 14)  <- NOT in memoir top-3
```

`score` is time-decayed (who is current); `raw` is before decay (who built it). When the raw top-n differs from the decayed top-n, both are shown. Options: `-n` number of experts, `--json` structured output with a full evidence record per author, `--now YYYY-MM-DD` reference date for reproducible output, `--repo` repository root.

**How often does blame lie?**

```sh
$ uv run memoir audit src --top 3
audit src: 738 tracked files; 0 file(s) last touched by a bot and 0 without human history excluded
blame lies: 26/738 files (3.5%) — last committer not in memoir top-3
  among contested files (more than 3 authors): 26/668 (3.9%)
worst cases (largest gap between top expert and last committer):
  src/vset.c: last Josh Soref 2026-08-12 (score 1.23) vs top Ran Shidlansik (score 8.28)
  …
```

Options: `--top` compare against top-n, `--worst` number of cases to list, `--now`, `--repo`.

**Index once, query in milliseconds**

```sh
$ uv run memoir index            # or: memoir index src   (limit to a directory)
indexed 14019 commits at 1a2b3c4d5e in 6.9 s -> .git/memoir/index.sqlite (3.7 MB)
```

One `git log --numstat -M` walk over the history is persisted under `.git/memoir/`, together with each file's lineage and its top-5 experts per list (used by `person` and kept current on update). `who` and `audit` always read from it: if it is missing they build it (seconds on most repositories, ~80 s on a 160k-commit one); if `HEAD` has moved they update it incrementally — only the new commits are walked, a fraction of a second — and say so on stderr; a rebased or amended `HEAD` triggers a full rebuild. `memoir index` builds it explicitly, optionally scoped to a directory; `--path` chooses another location.

**What does a person know?**

```sh
$ uv run memoir person "Viktor Söderqvist"        # name or email; split identities are merged and reported
Viktor Söderqvist — keys: viktor.soderqvist@est.tech, viktor@zuiderkwast.se
  files touched (at HEAD): 384; top-3 current: 200; top-3 built_it: 164; last touch 2026-08-13; ranks as of 2026-08-22; vendored excluded
  themes: hashtable, moduleapi, cluster, module, …
  current — can answer today:
    src/hashtable.c  #1 cur 7.30 · #1 raw 7.90
    …
  built_it — built it (undecayed):
    …
  directories (by expertise mass; top-3 current / built_it of files):
    tests/support/  8/13 (62%) · 5/13 (38%)  mass 22.0  e.g. stacktrace.tcl, server.tcl, cluster_util.tcl
```

A rollup, not a file list: the files where the person is in the top-3 (`current` = decayed, `built_it` = undecayed, always both), the directories ranked by expertise mass with a few representative files, and themes from path tokens (TF-IDF, no model). Vendored trees (`deps/`, `3rdparty/`, `vendor/` …) are excluded unless `--include-vendored`. `--json` for the full structure. Ranks come from the index's materialized per-file top-5 (computed at build/update time); `--now` outside the index's 30-day window recomputes live.

**Who should be pulled in for a set of files?**

```sh
$ git diff --name-only main... | uv run memoir experts --files -      # the files of a change
$ uv run memoir experts --dir src/cluster                              # an area
$ uv run memoir experts --match auth --prefix                          # a topic word in paths (authc, authz, ...)
121 files (path tokens cluster); ranks as of 2026-08-22
  e.g. src/cluster.c, src/cluster.h, src/cluster_legacy.c, ...
  current — can answer today:
    1. Binbin  69 files (57%)  mass 273  e.g. src/cluster_legacy.c
    2. Viktor Söderqvist  25 files (21%)  mass 66  e.g. src/cluster.c
  built_it — built it (undecayed):
    1. Binbin  67 files (55%)  mass 260  e.g. src/cluster_legacy.c
    2. antirez  15 files (12%)  mass 242  e.g. src/cluster.c
```

Selectors (`--dir`, `--glob`, `--match`, `--files`) combine; a person's mass sums their score over the files where they are top-3, more for #1 than #3 and more for contested files. A topic word only means what the paths say — the sample shows what matched — and a selection under 3 files is flagged as a file question. `--json` for the structure.

**Split identities**

```sh
$ uv run memoir identities          # suggested .mailmap lines, tiered (same name / GitHub noreply / spellings); nothing is written
```

Review, paste into `.mailmap`, rebuild the index. `person` already merges identities that share an email or a full name for its report and says so.

**For agents (MCP)**

memoir serves five tools over stdio: `who_knows(path, n=3)` → compact ranked answer (`current`, `recent`, `built_it` when it differs, trust flags); `expertise_evidence(path, author)` → full evidence record and rank for one person; `blame_divergence(path, n=3)` → whether the last committer holds the knowledge, explained; `person_profile(query, n=5)` → what a person knows; `experts_for_files(paths | dir | glob | match, n=5)` → who has the most expertise across a set of files (e.g. the files of a change). Paths are relative to the repository root; the index is built or updated on demand (stderr notice on the first call).

*Claude Code* — run inside the repository you want answers about (the server uses that repo; add `--repo PATH` to pin another):

```sh
claude mcp add memoir -- uv run --directory /path/to/memoir memoir mcp
claude mcp list            # or /mcp inside a session
```

Or commit it for the team as `.mcp.json` in the repository root:

```json
{ "mcpServers": { "memoir": { "command": "uv",
    "args": ["run", "--directory", "/path/to/memoir", "memoir", "mcp"] } } }
```

*GitHub Copilot (VS Code agent mode)* — `.vscode/mcp.json` in the repository (or add via the "MCP: Add Server" command):

```json
{ "servers": { "memoir": { "type": "stdio", "command": "uv",
    "args": ["run", "--directory", "/path/to/memoir", "memoir", "mcp"] } } }
```

*Claude Desktop* — `claude_desktop_config.json`, pinning the repo since Desktop has no working directory:

```json
{ "mcpServers": { "memoir": { "command": "uv",
    "args": ["run", "--directory", "/path/to/memoir", "memoir", "mcp", "--repo", "/path/to/your-repo"] } } }
```

If `uv` is not on the PATH the host app uses, give its full path (e.g. `~/.local/bin/uv`). Only stdout is the MCP protocol; memoir's notices go to stderr.

## How it scores (v0)

For each (file, author) over the file's full history, excluding bot authors, pure merges, and content-free commits (renames, mode changes):

```
raw   = 3.0 · first_authored + 1.0 · log(1 + deliveries) + 0.5 · log(1 + lines)
        − 0.7 · log(1 + commits_by_others_since_last_touch)
score = max(0, raw) · 0.5 ^ (months_since_last_touch / 18)
```

with, as of the P6 gate: a commit touching *B* files counts as `min(1, 10/B)` of a commit (for credit, lines, and the erosion it causes others — sweeps carry little knowledge); lines per commit are capped at 300 before the size term; `first_authored` earns its +3 unless the creating commit is the repository's root commit (bulk imports). `deliveries` = commits + 0.5 × co-authored commits (`Co-authored-by:` trailers, including on bot-authored commits). Identities resolve through `.mailmap`; placeholder emails fall back to name. Every shape is a field of `scoring.Weights`; `scoring.V0` is the original formula. Evidence per author: `score, raw_score, first_authored, first_credited, commits, coauthored_count, lines_changed, active_span, last_touch, months_since_last_touch, others_commits_since`. `who --json` also returns labeled lists — `current` (decayed: who can answer today), `built_it` (raw: deepest accumulated knowledge), `recent` (the last distinct humans, i.e. the recency baseline) — and trust flags (`dormant`, `last_touch_is_sweep`, `stability` across half-lives).

Evaluation against five public repositories is in [eval/results.md](eval/results.md); performance baseline and index benchmarks in [eval/perf.md](eval/perf.md); the scoring-change harness and measured proposals in [eval/proposals.md](eval/proposals.md) and [eval/regress/](eval/regress/); the fix-commit replay in [eval/replay.md](eval/replay.md); design notes and decisions in [agent_notes.md](agent_notes.md).

## Open questions

## Related research

The scoring shape descends from degree-of-authorship / degree-of-knowledge research: Fritz, Ou, Murphy & Murphy-Hill, "A Degree-of-Knowledge Model to Capture Source Code Familiarity," ICSE 2010. memoir's formula is a variant of that shape, not their calibration.

## Worth exploring
