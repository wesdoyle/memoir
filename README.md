# memoir

memoir is a prototype codebase expert-identifier. It mines git history to find the people most likely to hold the mental model of a file. A basic CLI and MCP server provide results.

Basic methods of attribution (the blame gutter, `git log`) often mask long-term authors and maintaners behind lint sweeps, renames, and bot commits. As agents do more engineering work in legacy codebases, and as teams of humans collaborate in realtime engineering environments, knowing which humans should be pulled into the room is useful routing infra. memoir is a first pass at that answer.

## Quickstart

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/). No network access required. git is read through local repo commands only. The only state memoir writes is a search index under `.git/memoir/`.

```sh
git clone <this repo> memoir && cd memoir
uv sync
uv run pytest            # tests against a synthetic fixture repo
uv run memoir --help
```

## Usage

Install it once as a command, then run it inside any git repository (or point at one with `--repo`):

```sh
uv tool install --editable /path/to/memoir     # `memoir` on your PATH, tracking the checkout
cd /path/to/some-repo
memoir who src/foo.c
```

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

`score` is time-decayed (who is current); `raw` is before decay (who built it). When the raw top-n differs from the decayed top-n, both are shown. 

Options: `-n` number of experts, `--json` structured output with a full evidence record per author, `--now YYYY-MM-DD` reference date for reproducible output, `--repo` repository root.

**How often does git blame diverge from?**

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

**Who should be pulled in for a set of files?**

```sh
$ git diff --name-only main... | uv run memoir experts --files -      # the files of a change
$ uv run memoir experts --dir src/cluster                              # an area
$ uv run memoir experts --match auth --prefix                          # a topic word in paths (authc, authz, ...)
121 files (path tokens cluster); ranks as of 2026-08-22
  e.g. src/cluster.c, src/cluster.h, src/cluster_legacy.c, ...
  current — can answer today:
    1. Binbin  top-3 on 69 files (57%)  e.g. src/cluster_legacy.c
    2. Viktor Söderqvist  top-3 on 25 files (21%)  e.g. src/cluster.c
  built_it — built it (undecayed):
    1. Binbin  top-3 on 67 files (55%)  e.g. src/cluster_legacy.c
    2. antirez  top-3 on 15 files (12%)  e.g. src/cluster.c
```

**MCP Setup**

*Claude Code* — run inside the repository you want answers about (the server uses that repo; add `--repo PATH` to pin another):

```sh
claude mcp add memoir -- uv run --project /path/to/memoir memoir mcp
claude mcp list            # or /mcp inside a session
```

Or commit it for the team as `.mcp.json` in the repository root:

```json
{ "mcpServers": { "memoir": { "command": "uv",
    "args": ["run", "--project", "/path/to/memoir", "memoir", "mcp"] } } }
```

*GitHub Copilot (VS Code agent mode)* — `.vscode/mcp.json` in the repository (or add via the "MCP: Add Server" command):

```json
{ "servers": { "memoir": { "type": "stdio", "command": "uv",
    "args": ["run", "--project", "/path/to/memoir", "memoir", "mcp"] } } }
```

Use `--project`, not `--directory`: `--directory` changes the working directory to memoir itself. If `uv` is not on the PATH the host app uses, give its full path (e.g. `~/.local/bin/uv`).

## Related research

memoir's scoring takes inspiration from degree-of-authorship / degree-of-knowledge research. See Fritz, Ou, Murphy & Murphy-Hill, "A Degree-of-Knowledge Model to Capture Source Code Familiarity," ICSE 2010.

## Worth exploring

- Is an experts panel useful as a VS Code / other editor extension?
- CI or scheduled workflows for sending custom summaries of changes to relevance-ranked maintainers?
- GH integration; PRs and Issues often contain more interpretable insights than git alone
- Topic modeling / embedding project symbols could unlock search for experts by topic, useful for cold-start expert finding on new modules
