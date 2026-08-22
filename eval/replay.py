"""Offline fix-commit replay: does memoir predict who ends up fixing a file?

    uv run python eval/replay.py <repo> [n_events] [seed]      # default 1000 events, seed 42

Events: non-merge, non-bot, non-sweep commits (breadth <= 20) whose subject looks like a fix
(FIX_RE). Responder = the commit's author. For each file the event touched, rebuild every
answer set from the file's history *as it was just before the event* (Index.history(before=pos))
and check whether the responder is in the top-k. Answer sets:

  v0          the spec formula (V0 weights)
  adopted     current defaults (breadth_k=10, line_cap=300, not_root)
  hl60        adopted with half_life 60
  raw         adopted without decay ("built_it")
  linescale   adopted + line_scale=20 (the pending flag)
  recency3    the last 3 distinct human authors before the event (the cheapest competitor)
  last        the last human author before the event (git log -1)
  mostcommits the 3 authors with the most commits before the event

Metrics: hit@1, hit@3, MRR over (event, file) pairs; paired sign test vs recency3 on hit@3;
the same on the subset where the last commit before the event was a sweep (breadth > 50).
Events with no prior file history (new files) are skipped — nothing to predict from.
"""

from __future__ import annotations

import random
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from memoir.index import default_index_path, open_index
from memoir.scoring import V0, Weights, rank

ROOT = Path(__file__).resolve().parent.parent
REPOS = ROOT / "eval" / "repos"
FIX_RE = re.compile(r"\b(fix(es|ed|ing)?|bug|regression|crash|leak|race|hang)\b", re.I)
SWEEP = 50
MAX_EVENT_BREADTH = 20

ANSWERS = {
    "v0": V0,
    "adopted": Weights(),
    "hl60": Weights(half_life_months=60),
    "raw": Weights(half_life_months=1e9),
    "linescale": Weights(line_scale=20),
}


def _rank_of(names: list[str], who: str) -> int | None:
    return names.index(who) + 1 if who in names else None


def replay(repo: str, n_events: int = 1000, seed: int = 42) -> str:
    ix = open_index(default_index_path(REPOS / repo))
    rows = ix.con.execute(
        "SELECT pos, sha, name, email, ts, breadth FROM commits WHERE merge=0 AND breadth BETWEEN 1 AND ? ORDER BY pos",
        (MAX_EVENT_BREADTH,),
    ).fetchall()
    # subjects are not stored; read them from git in one call keyed by sha
    import subprocess
    subj = dict(
        line.split(" ", 1) for line in subprocess.run(
            ["git", "-C", str(REPOS / repo), "log", "--format=%H %s"], capture_output=True, text=True
        ).stdout.splitlines() if " " in line
    )
    from memoir.mining import Identity
    cands = [r for r in rows if FIX_RE.search(subj.get(r[1], "")) and not Identity(r[2], r[3]).is_bot]
    events = random.Random(seed).sample(cands, min(n_events, len(cands)))
    per = {k: [] for k in list(ANSWERS) + ["recency3", "last", "mostcommits"]}  # list of ranks (None = miss)
    sweep_mask = []
    pairs = 0
    for pos, sha, name, email, ts, breadth in events:
        now = datetime.fromtimestamp(ts, tz=timezone.utc)
        responder = Identity(name, email)
        paths = [p for (p,) in ix.con.execute("SELECT path FROM files WHERE pos=?", (pos,)).fetchall()]
        for path in paths:
            h = ix.history(path, before=pos)
            if not h.authors:
                continue
            pairs += 1
            key = responder.key
            for k, w in ANSWERS.items():
                names = [e.author.key for e in rank(h, now=now, w=w)]
                per[k].append(_rank_of(names, key))
            by_recent = sorted(h.authors, key=lambda a: a.last_touch, reverse=True)
            recency = [a.author.key for a in by_recent]
            per["recency3"].append(_rank_of(recency[:3], key))
            per["last"].append(_rank_of(recency[:1], key))
            most = [a.author.key for a in sorted(h.authors, key=lambda a: (-a.commits, a.author.name))]
            per["mostcommits"].append(_rank_of(most[:3], key))
            last = h.last_commit
            sweep_mask.append(bool(last and last.breadth is not None and last.breadth > SWEEP))
    ix.close()

    def metrics(ranks):
        n = len(ranks)
        h1 = sum(1 for r in ranks if r == 1) / n if n else 0
        h3 = sum(1 for r in ranks if r is not None and r <= 3) / n if n else 0
        mrr = sum(1 / r for r in ranks if r is not None) / n if n else 0
        return h1, h3, mrr

    def sign_test(a, b):
        """paired on hit@3: (#a-only hits, #b-only hits)"""
        ao = sum(1 for x, y in zip(a, b) if (x is not None and x <= 3) and not (y is not None and y <= 3))
        bo = sum(1 for x, y in zip(a, b) if (y is not None and y <= 3) and not (x is not None and x <= 3))
        return ao, bo

    L = [f"## {repo} — {len(events)} fix events (of {len(cands)} candidates), {pairs} (event, file) pairs, seed {seed}", "",
         "| answer set | hit@1 | hit@3 | MRR | vs recency3 (wins / losses on hit@3) | sweep-last subset hit@3 (n) |", "|---|---|---|---|---|---|"]
    sw_idx = [i for i, m in enumerate(sweep_mask) if m]
    for k, ranks in per.items():
        h1, h3, mrr = metrics(ranks)
        w, l = sign_test(ranks, per["recency3"]) if k != "recency3" else ("–", "–")
        sw = metrics([ranks[i] for i in sw_idx])[1] if sw_idx else 0
        L.append(f"| {k} | {h1:.3f} | {h3:.3f} | {mrr:.3f} | {w} / {l} | {sw:.3f} ({len(sw_idx)}) |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    repo = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 42
    print(replay(repo, n, seed))
