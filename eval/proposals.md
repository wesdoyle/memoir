# Scoring proposals, measured (P6)

Workflow: `eval/regress.py` produces a fixed report from the on-disk indexes (`now` pinned to 2026-08-21, seed 42); every candidate is a `Weights` flag, default off; `eval/regress/diff_<candidate>.md` is the before/after against `eval/regress/baseline`. Defaults reproduce v0 byte-for-byte (the baseline was re-run after the facts restructure and was identical). None of this is ground truth; the canaries are regression tests, not targets. The replay in §7 is the arbiter.

Baseline canaries: antirez on server.c 25; Till Rohrmann on JobMaster.java 6; Shay Banon on the four ES files 33/32/34/38; Ran Shidlansik (1,293-line commit) on t_zset.c 2; Josh Soref in top-3 of Valkey's 30 busiest `src/*.c` 10 (the harness picks the 30 by index commit count; the earlier 9 used `rev-list`); Erich Gamma credited `first_authored` in the vscode audited dirs 82/393; creators credited in the 10 P4 dirs 2244/2244. Regression set: Alex Dima textModel.ts 1, Johannes Rieken event.ts 1, David Turner Node.java 1, Ryan Ernst Node.java 2, Vadim Pisarevsky matrix.cpp 1, Madelyn Olson config.c 1. Roster: top-1 21/30, top-3 slots 58/90.

## 1. Sweeps — discount by commit breadth

**Flag** `breadth_k`: a commit touching *B* files is worth `min(1, breadth_k / B)` of a commit — for delivery credit, for its lines, **and for the erosion it causes others** (`others_commits_since` is breadth-weighted in `rank()`). Rationale for eroding less: a sweep does not displace anyone's knowledge of the file; it is noise on the timeline. Breadth comes from the walk (index); per-file `--follow` mining has no breadth, so the live path applies no discount (documented; the index is the primary engine).

| | baseline | `breadth_k=10` | `breadth_k=30` |
|---|---|---|---|
| Josh Soref in top-3 of 30 busiest | 10 | **4** | 8 |
| Ran Shidlansik on t_zset.c | 2 | 3 | 2 |
| antirez / Till / Shay (IndexMetadata) | 25 / 6 / 33 | 24 / 6 / 30 | 25 / 6 / 31 |
| regression set | all hold | **Madelyn Olson config.c 1→2** (5.80 vs Binbin 5.83) | all hold |
| roster top-1 / top-3 slots | 21 / 58 | **23 / 61** | 22 / 60 |
| top-3 set changed (sample) | – | ES 23, flink 20, valkey 20, vscode 16, opencv 3 /100 | ES 21, flink 19, valkey 13, vscode 16, opencv 2 |
| who left top-3 most | – | Mark Vieira ×15 (ES build/infra sweeps), **Rufus Refactor ×14** (flink Spotless commits, breadth 6,155–11,013), Daniil Kashapov ×8 (valkey rename sweep), Benjamin Pasero ×4 | same names, smaller counts |
| audit HL18 all-files, valkey src | 26/738 | **187/738** | – |
| audit HL18, ES cluster | 20/387 | 80/387 | – |

Reading. This is the single most effective change against the symptom, and the movement is accounted for: the names that leave are sweep accounts (`Rufus Refactor` is `dev@flink.apache.org` running Spotless). The audit "blame lies" rate jumps from 3.5% to 25% on valkey `src` — that is the stat finally measuring what it was meant to (the last committer is a sweep on a quarter of the files) rather than agreeing with blame by construction. Cost: Madelyn Olson's #1 on `config.c` becomes #2 by 0.03; her standing there is 3 commits / 1,573 lines, 591 of them in 6 commits with breadth > 10, versus Binbin's 28 commits / 296 lines — the regression case was thinly held and partly size- and breadth-driven. I would not call that a regression; I would call it the harness doing its job, and I would keep `config.c` in the set as "Madelyn or Binbin in top-2".

Trade-off with legitimate owner refactors: an owner's 500-file refactor is discounted to 1/50 of a commit per file — but owners have other, narrow commits on the files they own, and the discount is per commit, not per person, so their standing survives (Madelyn, Shay, Vadim all hold). The loser is someone whose *only* relationship to a file is wide commits — which is the definition of a sweep. `k=10` vs `k=30`: 10 is the right order (Soref's commits are 15–50 files; Kashapov's rename sweep hundreds); 30 leaves most of the symptom in place. **Recommend `breadth_k=10` as the new default**, pending §7.

## 2. Trivial and giant commits — per-commit floor and ceiling

**Flags** `line_scale` (delivery credit per commit = `1 − exp(−lines/line_scale)`, so a 1-line commit earns 0.05 deliveries at scale 20, a 20-line commit 0.63, a 100-line commit 0.99; binary files count as full) and `line_cap` (lines per commit capped before the size term: `log1p(Σ min(lines, cap))`). Shapes, not caps: the first is a saturating ramp (credit grows with evidence of engagement and saturates — a 1,000-line commit is one delivery, not ten); the second keeps the size term but makes any single commit's contribution to it bounded.

| | baseline | `line_scale=20` | `line_cap=300` | both |
|---|---|---|---|---|
| Josh Soref in top-3 | 10 | **5** | 10 | 5 |
| Ran Shidlansik on t_zset.c | 2 | 2 | **3** | 2 (!) |
| antirez / Shay (IndexMetadata) | 25 / 33 | 21 / 27 | 25 / 33 | 21 / 27 |
| regression set | – | all hold | **Madelyn config.c 1→2** | Madelyn 1→2 |
| roster top-1 / slots | 21 / 58 | 21 / 57 | 21 / 58 | 21 / 57 |
| top-1 changed (sample) | – | ≤5/100 everywhere | 0 everywhere | ≤5 |

Reading. `line_scale=20` halves the sweep symptom with almost no rank movement elsewhere (≤5% top-1 changes) and nudges founders up because many 1–2-line "others since" commits now also matter less... no — erosion is not line-shaped (by design: a 1-line fix by someone else is still evidence they touched it); founders move because their large commits keep full credit while others' small ones shrink. `line_cap=300` is surgical: it moves exactly the 1,293-line case (2→3) and Madelyn (1→2, same mechanism, same thin margin) and nothing else in the samples. Under both, Ran Shidlansik goes back to 2 because the cap removes less than the scale adds back for others. **Recommend `line_scale=20` (shape) and `line_cap=300` (bound) together, but it is a smaller win than breadth and overlaps with it** (both hit Soref). Order of adoption: breadth first, then re-measure these on top of it.

## 3. Decay erasing depth

Models, and what each assumes about memory:

- **v0 (pure half-life on everything)**: knowledge is a single perishable quantity; ten years of authorship and one commit fade at the same rate to zero. Matches recall of *detail* (exact code), not of *structure*.
- **Floor** (`decay_floor=f`: multiplier `f + (1−f)·0.5^(t/HL)`): knowledge fades to a retained fraction of its peak and stays there. Assumes consolidated long-term memory: someone who wrote a subsystem can re-derive it years later; they are not current, but they are not at zero. Simple, one parameter, preserves ordering within the stale group by raw score.
- **Depth-dependent half-life** (`decay_depth=d`: `HL_eff = HL·(1 + d·log1p(deliveries))`): deep practice is forgotten more slowly (spacing/over-learning). With d=0.5, a 778-commit history gets HL≈78 months; a 2-commit one stays at ≈22. Assumes the *rate* of forgetting depends on how much was learned, which is the better-supported model of human memory, but it is a stronger claim about git history as a proxy for learning.
- **Decay only some terms** (not implemented): keep `first_authored` and size undecayed (structural knowledge), decay deliveries (operational currency). Assumes two memories; it is really a two-list answer (see §5) folded into one number.

| | baseline | `decay_floor=0.25` | `decay_depth=0.5` |
|---|---|---|---|
| antirez / Till / Shay (IndexMetadata, Node) | 25 / 6 / 33, 38 | **8 / 1 / 10, 17** | **3 / 1 / 17, 32** |
| Josh Soref in top-3 | 10 | 7 | 3 |
| regression set | – | all hold | all hold |
| roster top-1 / slots | 21 / 58 | 21 / **53** | 20 / **46** |
| top-1 changed (sample) | – | flink 30, valkey 21, opencv 20, ES 14, vscode 7 /100 | valkey 12, opencv 9, ES 8, vscode 7, flink 6 |
| who enters top-3 | – | antirez ×4, Vadim Pisarevsky ×7, Stephan Ewen ×2, Shay Banon ×2, Pieter Noordhuis ×2 | antirez ×4, Vadim ×3, Stephan Ewen ×3, Oran Agra ×2 |
| audit HL18 all-files, valkey src | 26/738 | 46/738 | 46/738 |

Reading. Both do what they claim: founders come back into the top-10 (floor) or top-3 (depth); the regression set holds; the sweep symptom shrinks as a side effect because founders displace sweep authors. The cost is visible in the one outside signal we have: Valkey MAINTAINERS overlap in top-3 slots drops from 58 to 53 (floor) and 46 (depth) — antirez, Oran Agra, Pieter Noordhuis are not current maintainers. That is the crux: **these changes move the answer from "who is current" toward "who built it", and the roster says the current people are the right answer for "who do I ask"**. I believe the floor model of memory (f≈0.2–0.3) and think the depth model overstates git-as-learning; but I do not think either should be the default of a single list. They are the right decay regime for a *second* list — §5.

## 4. Dormant files — say so (done)

`who` now computes idle = months since the last knowledge-bearing human touch; if idle > 36 (two half-lives, so every decayed score is under a quarter of its raw value) it prints `dormant: no knowledge-bearing change for N months ...; ordered by raw score (who built it)`, orders by raw, suppresses the "by raw" line (redundant), and the JSON carries `dormant`, `dormant_months`, `ranked_by`. valkey `lzf_c.c` (idle 57 mo) now leads with antirez (created, 303 lines) instead of sundb (13 lines). Scores are unchanged, so the harness is unaffected.

## 5. One list or several

Recency is a signal that belongs in its own labeled answer, not a bias to be compromised away with one half-life. Tuning HL trades the roster (current people) against the founders (depth), and §3 shows there is no single value that serves both. Proposed answer shape, each list with its own regime and its own claim:

| list | regime | claim | use |
|---|---|---|---|
| `current` | v0 decay, HL 18, with the §1/§2 shapes | "has touched this file substantively and recently; can answer today" | routing, review requests, escalation |
| `built_it` | raw (no decay), same shapes | "holds the deepest accumulated knowledge, regardless of recency" | archaeology, legacy modernization, "why is it like this" |
| `recent` | last N distinct humans by last substantive touch, no scoring | "the pure-recency baseline; what blame/log would say" | the competitor memoir has to beat; shown so an agent can see when memoir disagrees with it |
| flags | `dormant`, `last_touch_is_sweep` (breadth of the last commit), `stability` (does top-1 survive HL ∈ {12, 18, 36, ∞}) | "how much to trust the above" | confidence for agents |

`who` keeps showing the first two; the MCP payload (P3) returns all of it. The half-life debate then becomes per-list, and §7 measures each list against its own criterion (current → who reviews; built_it → who fixes deep bugs; recent → the baseline).

## 6. First authorship on imports — the rule

**Flag** `first_rule`: `any` (v0) | `not_root` | `not_mass` (creating commit touched > `first_mass_n`=200 files) | `needs_followup` (creator has at least one later substantive commit). Measured on the 10 P4 directories (2,244 files with a creator):

| rule | creators still credited | Erich Gamma credited (vscode dirs) | canary moves | top-1 changed (sample) |
|---|---|---|---|---|
| `any` | 2244 | 82/393 | – | – |
| `not_root` | 2103 (−141, 6%) | **0** | none | ≤2/100 |
| `not_mass` 200 | 1699 (−545, 24%) | **0** | **Shay Banon worse** (33→35, 38→42): his bulk commits were his own work | ≤10/100 |
| `needs_followup` | 1428 (−816, 36%) | 4 | none | 5–18/100 |

Reading. `not_root` is precise for the vscode case (the import *is* the root) and touches 6% of files; it is obviously right and changes nothing in the HL18 audits (the +3 is decayed away there anyway; the effect is in raw/HL60, −6 divergent files on vscode editor/common). `not_mass` also catches imports that are not root commits (OpenCV's 2010 restructure, Flink's Stratosphere import) but penalizes prolific founders who committed in bulk, and Shay is the evidence. `needs_followup` removes credit from one-shot creators — a third of files — which is a different claim ("creating without returning is not knowledge") that I do not think holds. **Recommend `not_root`** now; consider `not_mass` with a higher threshold (1,000) if a non-root import case shows up in §7.

## 7. Validate, don't argue — the replay

Design, no code yet:

- **Data.** Per repo, a list of events `(time, file set, responder set)`: for review replay, merged PRs and their approvers (GitHub API, one-off, or `Reviewed-by:` trailers where used); for fix replay, commits whose message references an issue/bug (`Fixes #`, `FLINK-NNNN`, `[bug]`), responder = the author. Both deterministic once fetched; store as JSON under `eval/replay/<repo>.json`.
- **Replay.** For each event, build the ranking *as of the event's base commit*: the index is by `pos` (newest first), so "history before commit X" is `pos > pos(X)` — one extra predicate in `Index.history`, no rebuild. Score each answer set on whether the responder(s) are in its top-k (k = 1, 3): hit rate, and mean reciprocal rank.
- **Answer sets compared, per event:** `v0` (HL 18); `HL 60`; `raw`; the §1/§2 shapes on top of each; **`recency-N`: the last N distinct human committers before the event** (the cheapest competitor and the one most likely to win); `last-committer` (N=1); `most-commits-ever`. Also the `current`/`built_it` lists of §5 against their own criteria.
- **Report.** Per repo and pooled: hit@1, hit@3, MRR for each answer set; a paired comparison against `recency-3` with a sign test over events; and a breakdown on the subset where the last commit before the event is a sweep (breadth > 50) — the premise predicts memoir wins there by a lot; if it does not, memoir is not adding anything over `git log`.
- **Decision rule.** A change is adopted if it does not lose against its own baseline on hit@3 pooled and wins on the sweep subset; the half-life question is settled by which HL maximizes hit@3 for `current` and which maximizes fix-replay hit@3 for `built_it` — two answers, as §5 predicts.
- **Cost.** Fetching PR approvals needs network (your approval); trailers-only is offline but covers few repos. Replay itself is index-speed: thousands of events in seconds.

## Status after the gate (continued by direction)

- Adopted as defaults (commit `Adopt defaults`): `breadth_k=10`, `line_cap=300`, `first_rule=not_root`. `V0` is kept in `scoring.py` as the spec formula and the harness baseline. `eval/regress/diff_adopted.md`: Soref 10→4, Ran 2→3, Gamma 82→0, Shay 33→30, roster 21→23 / 58→62; regression holds except the Madelyn/Binbin 0.03 swap.
- `line_scale=20` stays a flag: on top of the adopted defaults it takes Soref 4→1 and moves ≤5% of top-1s, but costs 4 roster slots (`diff_adopted_linescale.md`). The replay decides.
- §5 implemented in `who --json`: `lists.current` / `lists.built_it` / `lists.recent` and `flags` (`dormant`, `dormant_months`, `last_touch_is_sweep`, `last_touch_breadth`, `stability.top1_by_half_life` over HL ∈ {12, 18, 36, ∞}). Text output unchanged apart from the dormancy line.
- §7 implemented offline as `eval/replay.py` (fix-commit replay; see ### §7 results: fix-commit replay, 1,000 events per repo (eval/replay.md)

hit@3 / hit@1, and paired wins/losses against recency-3 on hit@3:

| repo (pairs) | adopted | v0 | hl60 | raw | recency-3 | last committer | most commits | adopted vs recency-3 |
|---|---|---|---|---|---|---|---|---|
| valkey (1,702) | **.541** / .391 | .541 / .384 | .525 / .364 | .509 / .305 | .520 / .385 | .385 | .462 | **78 W / 43 L** |
| opencv (2,193) | .569 / .366 | .559 / .353 | .552 / .328 | .537 / .295 | **.577 / .425** | .425 | .491 | 44 W / 62 L |
| flink (2,685) | .493 / .304 | .495 / .288 | .483 / .267 | .476 / .251 | **.502 / .357** | .357 | .435 | 73 W / 98 L |
| elasticsearch (2,334) | .510 / .313 | .515 / .313 | .494 / .278 | .482 / .254 | .515 / **.352** | .352 | .452 | 91 W / 103 L |
| vscode (1,997) | **.754** / .525 | .744 / .509 | .746 / .499 | .738 / .485 | .728 / .523 | .523 | .680 | **130 W / 78 L** |

Sweep-last subset (last commit before the event had breadth > 50), hit@3 adopted vs recency-3: valkey .246 vs .185 (n=65), opencv .387 vs .404 (349), flink .383 vs .386 (661), elasticsearch .385 vs .397 (514), vscode .698 vs .549 (162).

Reading, in order of confidence:

1. **Decay is right for "who will fix this next", and longer is worse.** `raw` and `hl60` lose to the adopted HL18 on every repo, on every metric. That settles the half-life debate for the `current` list: do not lengthen it. (It says nothing about `built_it`, whose criterion is not "who fixes next".)
2. **Adopted ≥ v0**: hit@1 up on 4/5 repos (equal on ES), hit@3 up on 3/5, flat on 2. The breadth/cap/not_root changes did not hurt predictive value and slightly helped. `line_scale=20` is flat-to-slightly-worse on hit@3 everywhere → leave it off.
3. **memoir beats `git log -1` and "most commits ever" everywhere** at k=3 (by 10–20 points), which is the floor the thesis needed to clear.
4. **memoir does not clearly beat the 3 most recent humans.** Wins with margin on valkey and vscode (sign tests ~p<0.01), loses narrowly on opencv and flink, ties on elasticsearch. At k=1 the last committer is a *better* single guess than memoir's #1 on opencv/flink/ES (.43/.36/.35 vs .37/.30/.31). Fixers are usually the people who just touched the file; a pure-recency list captures that and memoir's extra terms add little on top for this question.
5. **The sweep-last prediction held on 2/5.** Where a sweep was the last touch, memoir beats recency-3 on valkey (+6 pts) and vscode (+15) and is level elsewhere — recency-3 also survives a sweep because its second and third names are the pre-sweep people. The clearer win is against the single last committer (.08–.27 vs .25–.70).

Caveat on the criterion itself: fix replay is recency-biased by construction (people fix what they just changed), so it favours recency baselines; it measures `current`, not `built_it`. A review-routing replay (who is asked, rather than who acts) and a deep-bug subset (fix touching code untouched for > 2 years) are the criteria where depth should matter, and neither is run yet — the first needs network.

What this does to the thesis: the strong form ("memoir's ranking beats last-touch") holds at k=3 against `git log -1` on all five repos, and against the 3-most-recent-humans baseline on two of five. The honest statement today is: **memoir is a cheap, deterministic, well-behaved recency-plus-depth signal that is never worse than the naive baselines and sometimes better, with the useful property that it can say when it disagrees with recency (`lists.recent`, `flags`)** — not yet a demonstrated large improvement over the cheapest competitor on the one proxy we can run offline.
 below). PR-approval replay needs network and is not built.

### §7 results: fix-commit replay, 1,000 events per repo (eval/replay.md)

hit@3 / hit@1, and paired wins/losses against recency-3 on hit@3:

| repo (pairs) | adopted | v0 | hl60 | raw | recency-3 | last committer | most commits | adopted vs recency-3 |
|---|---|---|---|---|---|---|---|---|
| valkey (1,702) | **.541** / .391 | .541 / .384 | .525 / .364 | .509 / .305 | .520 / .385 | .385 | .462 | **78 W / 43 L** |
| opencv (2,193) | .569 / .366 | .559 / .353 | .552 / .328 | .537 / .295 | **.577 / .425** | .425 | .491 | 44 W / 62 L |
| flink (2,685) | .493 / .304 | .495 / .288 | .483 / .267 | .476 / .251 | **.502 / .357** | .357 | .435 | 73 W / 98 L |
| elasticsearch (2,334) | .510 / .313 | .515 / .313 | .494 / .278 | .482 / .254 | .515 / **.352** | .352 | .452 | 91 W / 103 L |
| vscode (1,997) | **.754** / .525 | .744 / .509 | .746 / .499 | .738 / .485 | .728 / .523 | .523 | .680 | **130 W / 78 L** |

Sweep-last subset (last commit before the event had breadth > 50), hit@3 adopted vs recency-3: valkey .246 vs .185 (n=65), opencv .387 vs .404 (349), flink .383 vs .386 (661), elasticsearch .385 vs .397 (514), vscode .698 vs .549 (162).

Reading, in order of confidence:

1. **Decay is right for "who will fix this next", and longer is worse.** `raw` and `hl60` lose to the adopted HL18 on every repo, on every metric. That settles the half-life debate for the `current` list: do not lengthen it. (It says nothing about `built_it`, whose criterion is not "who fixes next".)
2. **Adopted ≥ v0**: hit@1 up on 4/5 repos (equal on ES), hit@3 up on 3/5, flat on 2. The breadth/cap/not_root changes did not hurt predictive value and slightly helped. `line_scale=20` is flat-to-slightly-worse on hit@3 everywhere → leave it off.
3. **memoir beats `git log -1` and "most commits ever" everywhere** at k=3 (by 10–20 points), which is the floor the thesis needed to clear.
4. **memoir does not clearly beat the 3 most recent humans.** Wins with margin on valkey and vscode (sign tests ~p<0.01), loses narrowly on opencv and flink, ties on elasticsearch. At k=1 the last committer is a *better* single guess than memoir's #1 on opencv/flink/ES (.43/.36/.35 vs .37/.30/.31). Fixers are usually the people who just touched the file; a pure-recency list captures that and memoir's extra terms add little on top for this question.
5. **The sweep-last prediction held on 2/5.** Where a sweep was the last touch, memoir beats recency-3 on valkey (+6 pts) and vscode (+15) and is level elsewhere — recency-3 also survives a sweep because its second and third names are the pre-sweep people. The clearer win is against the single last committer (.08–.27 vs .25–.70).

Caveat on the criterion itself: fix replay is recency-biased by construction (people fix what they just changed), so it favours recency baselines; it measures `current`, not `built_it`. A review-routing replay (who is asked, rather than who acts) and a deep-bug subset (fix touching code untouched for > 2 years) are the criteria where depth should matter, and neither is run yet — the first needs network.

What this does to the thesis: the strong form ("memoir's ranking beats last-touch") holds at k=3 against `git log -1` on all five repos, and against the 3-most-recent-humans baseline on two of five. The honest statement today is: **memoir is a cheap, deterministic, well-behaved recency-plus-depth signal that is never worse than the naive baselines and sometimes better, with the useful property that it can say when it disagrees with recency (`lists.recent`, `flags`)** — not yet a demonstrated large improvement over the cheapest competitor on the one proxy we can run offline.


Post-gate cleanup (2026-08-22): the rejected flags (`line_scale`, `decay_floor`, `decay_depth`, `first_rule` values `not_mass`/`needs_followup`) were removed from `Weights`; the runs above remain reproducible from the committed `eval/regress/*.json` but the flags would have to be re-added to re-run them.

## Summary for the gate

| proposal | recommendation | evidence |
|---|---|---|
| 1 breadth discount | adopt `breadth_k=10` | Soref 10→4; sweep accounts leave top-3; roster up 21→23, 58→61; audit stat becomes meaningful (valkey 3.5%→25%); cost: Madelyn/Binbin swap by 0.03 on a thinly held case |
| 2 floor/ceiling | adopt `line_scale=20`, `line_cap=300` after 1, re-measure | Soref 10→5, Ran 2→3 (cap), ≤5% top-1 movement |
| 3 decay | do **not** change the single list; use floor (≈0.25) for a `built_it` list | founders return but roster slots drop 58→53/46 |
| 4 dormancy | done | `lzf_c.c` now explains itself |
| 5 lists | `current`, `built_it`, `recent` + flags | §3 shows one HL cannot serve both |
| 6 first-authored | adopt `not_root` | Gamma 82→0, 6% of files, no canary moves |
| 7 replay | build next, before MCP | the arbiter for everything above |
