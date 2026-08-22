# MEMOIR prototype 

We are building developer tooling called **memoir**, a research prototype. 
I will direct the project; you are the builder. We will work in phases -- 
stop at each phase gate for my review, and never expand scope. 

Keep notes about each phase and decision in an agent_notes.md file.
When in doubt about a decision, choose the smaller thing and note the cut in agent_notes.md.

## Thesis

As agentic coding helps software teams modernize legacy codebases, 
it's useful to download information from humans about hidden context that shaped the code.

While git blame and log show developers and agents who last touched a line, 
memoir tells us who is most likely to have the best understanding of the code. 
It mines git history deterministically to find the people most
likely to hold the mental model of a file, and serving that answer to
both humans and agents.

Motivation: knowledge about legacy codebases is trapped in the memoir of the 
people who built them. Last-touch attribution (as we see in editor tooling via the gutter) 
often masks long-term authors behind lint sweeps, renames, and bot commits. 
It's also difficult to quickly assess churn and long-term history from this tooling alone. 

As agents do more real engineering work, and as the engineering tooling surfaces become more 
multiplayer, "which human should be pulled into this conversation" should become routing infrastructure.  
This tooling could provide the basis for an agent's escalation path, decision gating, and context building.

## Open questions this prototype should help answer

These are open questions. Do not assume answers; we will discover them by building
and by running the tool on real repositories. I will steer at the decision gates. 
Revisit this list at every gate and note in agent_notes.md which questions have evidence yet.

1. What ground truth (if any) can validate an expertise ranking? 
   What would it take to falsify memoir's premise?
2. How often does the last committer 
   differ from the strongest inferred 
   expert candidate? When they differ, 
   is that signal or noise? 
3. What kinds of commits look like authorship 
   but carry no knowledge? What should the 
   scorer do about them?
4. What should the tool say about a file 
   that hasn't been changed in a long time? 
5. When memoir's ranking does not intersect the set of developers in a 
   CONTRIBUTORS file, which is right, and how would we even judge that?
6. How can an agent best use this over MCP? What does an agent need from the answer 
   that a human doesn't, and vice versa?

## Hard constraints

- Python 3.12, managed with uv. Deps: typer, fastmcp, pytest. Nothing else without asking.
- The core must be deterministic. No LLM calls anywhere in mining or scoring. Git access via subprocess plumbing commands only
  (e.g. `git log --follow --numstat`, `git blame --porcelain`).
- Rankings should be structured data containing metrics we can reason about.
- Use `.mailmap` for identity resolution. Filter bots 
  (e.g. `dependabot|renovate|\[bot\]|actions@github`) and pure merge commits. 
  Parse `Co-authored-by:` trailers and credit co-authors at reduced weight.
- Every phase ends with a commit. Commit messages should provide narrative for the proto build.

## Notes files

- **agent_notes.md** (yours): be concise. group notes under phase headings. 
  Include decisions made, scope cut, learnings and surprises, 
  and which of the open questions we are learning answers to. 
  Write in a direct and technical style similar to Postgres docs or TypeScript docs.
  No narrative or catchy content. If the whole file exceeds ~100 lines before prototype completion, 
  you are writing too much.
- **wes_notes.md** (mine): my private work log. Do not write to it. 

## Repo layout

```
memoir/
  README.md          # thesis + quickstart; grows at the final phase
  agent_notes.md
  pyproject.toml
  src/memoir/
    mining.py        # git history -> per-(file, author) raw facts
    scoring.py       # facts -> ranked experts with evidence
    cli.py           # memoir who / audit
    mcp_server.py    # agent surface
  tests/
    fixtures/        # tiny synthetic git repo built by a script
    test_scoring.py
  eval/
    results.md
```

## v0 scoring algorithm (implement exactly; tune weights only at my direction)

For each (file, author), from full `--follow` history:

```
raw = w_first * first_authored            # 1 if author created the file
    + w_del   * log(1 + deliveries)       # commits touching the file
    + w_size  * log(1 + lines_changed)
    - w_decay * log(1 + others_commits_since_authors_last)
score = raw * 0.5 ** (months_since_last_touch / HALF_LIFE_MONTHS)
```

Defaults: `w_first=3.0, w_del=1.0, w_size=0.5, w_decay=0.7,
HALF_LIFE_MONTHS=18`. `Co-authored-by` counts as 0.5 of a delivery.
Emit an evidence record per author: `{score, first_authored, commits,
lines_changed, active_span, last_touch, coauthored_count}`.

Lineage note: this scoring shape descends from degree-of-authorship
research; the README must credit it. Cite: Fritz, Ou, Murphy &
Murphy-Hill, "A Degree-of-Knowledge Model to Capture Source Code
Familiarity," ICSE 2010 (and note the formula here is a variant, not
their calibration). Do not survey the literature on your own
initiative — if and when a research pass is useful, I will direct it
at a gate.

## Surfaces (v0)

CLI (humans):
- `memoir who <path> [-n 3]` — ranked experts + one-line evidence each
- `memoir audit [<dir>]` — THE HEADLINE STAT: % of files whose last
  committer is NOT in the top-3 memoir experts (how often blame lies),
  plus the worst cases

MCP (agents): exactly three tools, mirroring a resolution ladder:
- `who_knows(path, n=3)` → compact ranked list (aim ~100 tokens)
- `expertise_evidence(path, author)` → full evidence record
- `blame_divergence(path)` → last-toucher vs. memoir top-3, explained

## Phases & gates (v0)

- **P0**: scaffold; fixture-repo script (synthetic history including a
  rename, a bot commit, a co-authored commit, and a lint sweep by a
  non-expert). STOP.
- **P1**: mining + scoring + pytest against the fixture (the
  lint-sweeper must NOT outrank the long-term author; the renamed file
  must retain its history). STOP.
- **P2**: CLI `who` + `audit`; smoke-test on this repo itself. STOP.
- **P3**: MCP server, three tools. STOP.
- **P4**: run the tool against 5 real public repos I approve at the
  gate; record the audit stat and every surprising ranking in
  eval/results.md; propose (do not implement!) how the premise could be
  validated or falsified (question 1). STOP. This is v0.

Direction beyond v0 comes from me, driven by what the open questions turn up.

## Non-goals and boundaries

- No network calls except git clones I approve
- No UI for now
- No persistence or caching

