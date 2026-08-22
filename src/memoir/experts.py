"""Expertise over a set of files: who should be pulled in for this change / this area.

Selectors (ANDed): a directory, a glob, path-token match words (OR across words; --prefix for
stems), an explicit file list (a PR diff, `grep -l` output). The aggregation is the same as
`person`'s but transposed: for each selected file, the materialized top-5 rows; a person's mass is
Σ score/rank (current) or Σ raw/rank (built_it) over files where they are top-3 — being #1 on a file
counts more than #3 — weighted by log1p(authors) so contested files count more than sole-author dumps. Identities sharing a full name are merged
for the report. A tiny selection is flagged: that is a file answer (`who`), not a set answer.
"""

from __future__ import annotations

import fnmatch
import math
import re
from collections import defaultdict
from datetime import datetime, timezone

from memoir.index import Index
from memoir.person import VENDORED, _norm_name, _tokens
from memoir.scoring import rank

TOP = 3
TINY = 3


def _all_files(ix: Index, include_vendored: bool) -> list[str]:
    paths = [p for (p,) in ix.con.execute("SELECT DISTINCT path FROM file_lineage")]
    return sorted(p for p in paths if include_vendored or not VENDORED.search(p))


def select_files(ix: Index, dir: str | None = None, glob: str | None = None, match: list[str] | None = None,
                 prefix: bool = False, files: list[str] | None = None, include_vendored: bool = False) -> tuple[list[str], str]:
    """Apply the selectors (ANDed) to the files at HEAD. Returns (paths, human description)."""
    paths = _all_files(ix, include_vendored)
    parts = []
    if dir:
        d = dir.strip("/")
        paths = [p for p in paths if d == "." or p == d or p.startswith(d + "/")]
        parts.append(f"under {d}/")
    if glob:
        paths = [p for p in paths if fnmatch.fnmatch(p, glob) or fnmatch.fnmatch(p.rsplit("/", 1)[-1], glob)]
        parts.append(f"matching {glob}")
    if match:
        words = [w.lower() for w in match]
        def hit(p):
            toks = _tokens(p, stop=set())
            return any((t.startswith(w) if prefix else t == w) for t in toks for w in words)
        paths = [p for p in paths if hit(p)]
        parts.append(("path tokens starting with " if prefix else "path tokens ") + "/".join(words))
    if files is not None:
        wanted = {f.strip().lstrip("./") for f in files if f.strip()}
        paths = [p for p in paths if p in wanted]
        skipped = len(wanted) - len(paths)
        parts.append(f"{len(wanted)} listed files" + (f", {skipped} skipped: not at HEAD or vendored" if skipped else ""))
    return paths, ", ".join(parts) or "all files"


def experts_report(ix: Index, paths: list[str], n: int = 10, now: str | datetime | None = None) -> dict:
    if isinstance(now, str):
        now = datetime.fromisoformat(now).replace(tzinfo=timezone.utc)
    when = now or datetime.now(tz=timezone.utc)
    live = not ix.ranks_fresh(when)
    # identity merge for the report: identities sharing a normalized multi-token name collapse
    groups: dict[str, str] = {}
    def gid(key: str, name: str) -> str:
        nm = _norm_name(name)
        return f"name:{nm}" if len(nm.split()) >= 2 else key
    cur = defaultdict(lambda: {"mass": 0.0, "files": 0, "keys": set(), "name": None, "best": None})
    built = defaultdict(lambda: {"mass": 0.0, "files": 0, "keys": set(), "name": None, "best": None})
    for p in paths:
        n_auth = ix.con.execute(
            "SELECT COUNT(DISTINCT LOWER(c.email)) FROM file_lineage l JOIN commits c ON c.pos=l.pos WHERE l.path=? AND c.merge=0",
            (p,)).fetchone()[0]
        w = math.log1p(n_auth or 1)
        if live:
            r = rank(ix.history(p), now=when, w=ix.rank_weights)
            by_raw = sorted(r, key=lambda e: (-e.raw_score, e.author.name))
            rows = [(e.author.key, e.author.name, e.author.email,
                     next((i for i, x in enumerate(r, 1) if x.author.key == e.author.key), None), e.score,
                     next((i for i, x in enumerate(by_raw, 1) if x.author.key == e.author.key), None), e.raw_score)
                    for e in r[:5] + [x for x in by_raw[:5] if x not in r[:5]]]
        else:
            rows = ix.ranks_for(p)
        for key, name, email, rc, sc, rr, raw in rows:
            g = gid(key, name)
            if rc is not None and rc <= TOP:
                a = cur[g]; a["mass"] += sc * w / rc; a["files"] += 1; a["keys"].add(email); a["name"] = a["name"] or name
                if a["best"] is None or sc > a["best"][1]:
                    a["best"] = (p, sc)
            if rr is not None and rr <= TOP:
                a = built[g]; a["mass"] += raw * w / rr; a["files"] += 1; a["keys"].add(email); a["name"] = a["name"] or name
                if a["best"] is None or raw > a["best"][1]:
                    a["best"] = (p, raw)

    def out(d):
        rows = sorted(d.values(), key=lambda a: (-a["mass"], -a["files"], a["name"] or ""))[:n]
        return [{"name": a["name"], "emails": sorted(a["keys"]), "files_top3": a["files"], "mass": round(a["mass"], 1),
                 "share": round(a["files"] / len(paths), 3) if paths else 0.0,
                 "best_file": a["best"][0] if a["best"] else None} for a in rows]

    note = None
    if not paths:
        note = "no files selected"
    elif len(paths) < TINY:
        note = f"only {len(paths)} file(s) selected: this is a file answer — use `memoir who` for the evidence"
    return {
        "selection": {"files": len(paths), "sample": sorted(paths, key=len)[:8],
                      "ranks_as_of": (when if live else ix.rank_now).date().isoformat()},
        "current": out(cur), "built_it": out(built), "note": note,
    }


def format_experts(rep: dict, desc: str) -> str:
    s = rep["selection"]
    L = [f"{s['files']} files ({desc}); ranks as of {s['ranks_as_of']}"]
    if s["sample"]:
        L.append("  e.g. " + ", ".join(s["sample"][:6]))
    if rep["note"]:
        L.append(f"  note: {rep['note']}")
    for label, title in (("current", "can answer today"), ("built_it", "built it (undecayed)")):
        L.append(f"  {label} — {title}:")
        if not rep[label]:
            L.append("    (nobody in the top-3 of any selected file)")
        for i, e in enumerate(rep[label], 1):
            L.append(f"    {i}. {e['name']}  {e['files_top3']} files ({e['share']:.0%})  mass {e['mass']:.0f}  e.g. {e['best_file']}")
    return "\n".join(L)
