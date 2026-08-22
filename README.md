# memoir

memoir is a prototype codebase expert-identifier. It mines git history deterministically to find the people most likely to hold the mental model of a file, and serves that answer to humans (CLI) and, later, to agents (MCP).

Last-touch attribution — the blame gutter, `git log -1` — often masks long-term authors behind lint sweeps, renames, and bot commits. As agents do more engineering work in legacy codebases, "which human should be pulled into this conversation" becomes routing infrastructure: an escalation path, a decision gate, a source of hidden context. memoir is a first pass at that answer.

## Quickstart

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/). No network access, no LLM calls, no caching; git is read through plumbing commands only.

```sh
git clone <this repo> memoir && cd memoir
uv sync
uv run pytest            # 44 tests against a synthetic fixture repo
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

Options: `--top` compare against top-n, `--worst` number of cases to list, `--now`, `--repo`. Cost is one `git log --follow` per file (0.01–3 s depending on history depth), so scope the directory on large repos.

## How it scores (v0)

For each (file, author) over the file's full `--follow` history, excluding bot authors, pure merges, and content-free commits (renames, mode changes):

```
raw   = 3.0 · first_authored + 1.0 · log(1 + deliveries) + 0.5 · log(1 + lines_changed)
        − 0.7 · log(1 + commits_by_others_since_last_touch)
score = max(0, raw) · 0.5 ^ (months_since_last_touch / 18)
```

`deliveries` = commits + 0.5 × co-authored commits (`Co-authored-by:` trailers, including on bot-authored commits). Identities resolve through `.mailmap`; placeholder emails fall back to name. Evidence per author: `score, raw_score, first_authored, commits, coauthored_count, lines_changed, active_span, last_touch, months_since_last_touch, others_commits_since`.

Evaluation against five public repositories is in [eval/results.md](eval/results.md); design notes and decisions in [agent_notes.md](agent_notes.md).

## Open questions

## Related research

The scoring shape descends from degree-of-authorship / degree-of-knowledge research: Fritz, Ou, Murphy & Murphy-Hill, "A Degree-of-Knowledge Model to Capture Source Code Familiarity," ICSE 2010. memoir's formula is a variant of that shape, not their calibration.

## Worth exploring
