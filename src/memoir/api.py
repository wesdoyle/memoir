"""Shared answer logic for the CLI and MCP surfaces.

Source:        the repository's on-disk index, built or refreshed on demand (one-line stderr notice).
answer():      FileHistory + ranking + divergence for a path (dormant files are ordered by raw score).
lists_and_flags(): the labeled lists (current / built_it / recent) and trust flags.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from memoir.index import Index, build_index, default_index_path, open_index, update_index
from memoir.mining import FileHistory
from memoir.scoring import Evidence, Weights, divergence, months_between, rank

def fmt_expert(i: int, e: Evidence) -> str:
    bits = []
    if e.first_authored:
        bits.append("created")
    bits.append(f"{e.commits} commit{'s' if e.commits != 1 else ''}")
    if e.coauthored_count:
        bits.append(f"{e.coauthored_count} co-authored")
    bits.append(f"{e.lines_changed} lines")
    bits.append(f"last {e.last_touch} ({e.months_since_last_touch:.0f} mo ago)")
    if e.others_commits_since:
        bits.append(f"{e.others_commits_since:g} by others since")
    return f"{i}. {e.author.name} <{e.author.email}>  score {e.score:.2f} (raw {e.raw_score:.2f})  " + " · ".join(bits)


def by_raw(ranked: list[Evidence]) -> list[Evidence]:
    return sorted(ranked, key=lambda e: (-e.raw_score, e.author.name, e.author.email))


class Source:
    """The on-disk index for a repository; built or refreshed on demand with a one-line notice."""

    def __init__(self, root: Path, need: str | None = None):
        self.root = root
        self.db = default_index_path(root)
        self.index: Index | None = None
        reason = action = None
        if not self.db.exists():
            reason, action = "no index yet", "build"
        else:
            ix = open_index(self.db)
            if need is not None and not ix.covers(need):
                reason, action = f"index covers only {ix.pathspec}", "build"
            elif not ix.is_fresh(root):
                reason, action = f"index is stale (at {ix.head[:10]}, HEAD differs)", "update"
            ix.close()
            if action is None:
                self.index = ix if False else open_index(self.db)
        if action == "build":
            print(f"memoir: {reason}; building index for {root} ...", file=sys.stderr, flush=True)
            build_index(root, self.db)
        elif action == "update":
            print(f"memoir: {reason}; updating index for {root} ...", file=sys.stderr, flush=True)
            how = update_index(root, self.db)
            if how == "rebuilt":
                print("memoir: HEAD is not a descendant of the indexed commit; rebuilt from scratch", file=sys.stderr, flush=True)
        if self.index is None:
            self.index = open_index(self.db)
        self.name = "index"

    def history(self, rel: str) -> FileHistory:
        assert self.index is not None
        return self.index.history(rel)

    @property
    def head(self) -> str:
        assert self.index is not None
        return self.index.head

    def close(self) -> None:
        if self.index is not None:
            self.index.close()


DORMANT_MONTHS = 36.0  # 2 half-lives: every decayed score is below a quarter of its raw value


def dormancy(h: FileHistory, now: datetime | None) -> tuple[bool, float]:
    """(dormant, months since the last knowledge-bearing human touch)."""
    now = now or datetime.now(tz=timezone.utc)
    if not h.authors:
        return False, 0.0
    idle = min(months_between(a.last_touch, now) for a in h.authors)
    return idle > DORMANT_MONTHS, idle


SWEEP_BREADTH = 50  # a last commit touching more files than this is flagged as a sweep
STABILITY_HALF_LIVES = {"12": 12.0, "18": 18.0, "36": 36.0, "inf": 1e9}


def lists_and_flags(h: FileHistory, ranked: list[Evidence], n: int, now: datetime | None) -> tuple[dict, dict]:
    """Proposal 5: labeled answers, each with the decay regime that fits its question, plus trust flags."""
    recent, seen = [], set()
    for a in sorted(h.authors, key=lambda a: a.last_touch, reverse=True):
        if a.author.key not in seen:
            seen.add(a.author.key)
            recent.append({"name": a.name, "email": a.email})
        if len(recent) >= n:
            break
    top1_by_hl = {k: (r[0].author.name if (r := rank(h, now=now, w=Weights(half_life_months=hl))) else None)
                  for k, hl in STABILITY_HALF_LIVES.items()}
    dormant, idle = dormancy(h, now)
    last = h.last_commit
    flags = {
        "dormant": dormant,
        "dormant_months": round(idle, 1),
        "last_touch_is_sweep": bool(last and last.breadth is not None and last.breadth > SWEEP_BREADTH),
        "last_touch_breadth": last.breadth if last else None,
        "stability": {"top1_by_half_life": top1_by_hl, "top1_stable": len(set(top1_by_hl.values())) == 1},
    }
    lists = {
        "current": [e.to_dict() for e in ranked[:n]],          # decayed: can answer today
        "built_it": [e.to_dict() for e in by_raw(ranked)[:n]],  # raw: deepest accumulated knowledge
        "recent": recent,                                      # pure recency baseline: what blame/log says
    }
    return lists, flags


def answer(src: Source, rel: str, n: int, now: datetime | None) -> tuple[FileHistory, list[Evidence], dict]:
    """Rank; on a dormant file the decayed order is noise, so rank by raw score instead."""
    h = src.history(rel)
    ranked = rank(h, now=now)
    dormant, _ = dormancy(h, now)
    if dormant:
        ranked = by_raw(ranked)
    return h, ranked, divergence(h, ranked, n)
