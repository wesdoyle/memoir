"""The reverse question: what does this person know? A rollup, not a file list.

For person P (a set of identity keys): every HEAD file whose lineage contains a touch by P, P's rank
in that file's `current` (decayed) and `built_it` (raw) top-5 (from the materialized file_rank table),
then: top files per list, directories ranked by expertise mass, and TF-IDF themes over path tokens.
Vendored trees are excluded by default. Both lists are always present and labeled: a departed
founder is "built_it full, current empty".
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

from memoir.index import Index
from memoir.mining import Identity

TOP = 3
VENDORED = re.compile(r"(^|/)(3rdparty|third_party|thirdparty|deps|vendor|external|extern|node_modules)(/|$)", re.I)
STOP = set("src main java org com test tests unit integration include lib h c cpp hpp hxx cc ts js py rb md json txt "
           "yml yaml xml in cmake internal impl base core common util utils misc api v1 v2".split())
IDF_FLOOR = 0.2  # tokens present in more than this share of files (repo names, ubiquitous dirs) are not themes
DIR_TOKEN_WEIGHT = 1.0  # directory tokens carry module identity (imgproc, cluster); basename weighting tested worse


def _norm_name(n: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", n.lower()).strip()


def resolve_person(ix: Index, query: str) -> tuple[set[str], str | None]:
    """Exact email -> that identity. Else substring over names/emails; hits grouped by union-find over
    shared key (email) or shared normalized name. One group -> its keys (+ a note if several keys);
    several groups -> ambiguous; none -> no author."""
    q = query.lower()
    rows = ix.con.execute("SELECT name, email, COUNT(*) FROM commits GROUP BY name, email").fetchall()
    idents = [(Identity(n, e), c) for n, e, c in rows if not Identity(n, e).is_bot]
    exact = [(i, c) for i, c in idents if i.email.lower() == q]
    hits = exact or [(i, c) for i, c in idents if q in i.name.lower() or q in i.email.lower()]
    if not hits:
        return set(), f"no author matches {query!r}"
    parent: dict = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            x = parent[x]
        return x

    for i, _ in hits:
        parent[find(("k", i.key))] = find(("n", _norm_name(i.name)))
    groups = defaultdict(list)
    for i, c in hits:
        groups[find(("k", i.key))].append((i, c))
    if len(groups) > 1:
        cands = sorted({(i.name, i.email) for i, _ in hits})
        return set(), "ambiguous: " + "; ".join(f"{n} <{e}>" for n, e in cands[:12]) + (" ..." if len(cands) > 12 else "")
    keys = {i.key for i, _ in hits}
    if len(keys) == 1:
        return keys, None
    desc = ", ".join(f"{i.name} <{i.email}> ({c})" for i, c in sorted(hits, key=lambda x: -x[1]))
    return keys, f"merged {len(keys)} identities for this report: {desc}. Add them to .mailmap to make it permanent."


def _tokens(path: str, stop: set[str] | None = None) -> dict[str, float]:
    """token -> weight (1.0 if it occurs in the file name, else DIR_TOKEN_WEIGHT). `stop` defaults to STOP;
    pass an empty set when the user supplies the word (a requested `core` must match core/)."""
    if stop is None:
        stop = STOP
    last = path.rsplit("/", 1)[-1]
    stem = last.rsplit(".", 1)[0] if "." in last else last
    out: dict[str, float] = {}
    for part, wgt in [(path[: -len(last)], DIR_TOKEN_WEIGHT), (stem, 1.0)]:
        for piece in re.split(r"[/_\-. ]+", part):
            for t in re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+", piece):
                t = t.lower()
                if len(t) >= 3 and t not in stop:
                    out[t] = max(out.get(t, 0.0), wgt)
    return out


def _repo_stop(ix: Index) -> set[str]:
    """The repository's own name is not a theme (valkey-cli.c, opencv2/...)."""
    root = ix.meta.get("repo_name") or ""
    return {t for t in re.findall(r"[a-z]+", root.lower()) if len(t) >= 3}


def _head_files(ix: Index, include_vendored: bool) -> list[str]:
    paths = [p for (p,) in ix.con.execute("SELECT DISTINCT path FROM file_lineage")]
    return paths if include_vendored else [p for p in paths if not VENDORED.search(p)]


def person_report(ix: Index, keys: set[str], now: str | datetime | None = None, n_top: int = 8,
                  include_vendored: bool = False, live: bool | None = None) -> dict:
    """Build the rollup. Uses materialized ranks when `now` is None or within the index's rank freshness
    window; otherwise ranks live for the candidate files (seconds, not minutes)."""
    if isinstance(now, str):
        now = datetime.fromisoformat(now).replace(tzinfo=timezone.utc)
    when = now or datetime.now(tz=timezone.utc)
    use_live = (not ix.ranks_fresh(when)) if live is None else live
    existing = _head_files(ix, include_vendored)
    existing_set = set(existing)
    candidates = [p for p in ix.files_touched_by(keys) if p in existing_set]
    per: dict[str, dict] = {}
    for p in candidates:
        rows = [x for x in ix.file_ranks(p, when, live=use_live) if x[0] in keys]
        if not rows:
            continue  # P is not in the top-5 of either list: a record, but not strength
        # split identities can each hold a row on the same file; take the strongest (the .mailmap fix is the real one)
        x = max(rows, key=lambda x: (x[4], x[6]))
        per[p] = {"path": p, "rank_cur": x[3], "score": x[4], "rank_raw": x[5], "raw": x[6], "name": x[1],
                  "authors": ix.authors_of(p)}

    def strong_cur(v): return v["rank_cur"] is not None and v["rank_cur"] <= TOP
    def strong_raw(v): return v["rank_raw"] is not None and v["rank_raw"] <= TOP

    # summary
    last_touch = None
    if per:
        # last touch: newest commit by P in the lineage of any candidate file
        row = ix.con.execute(
            "SELECT MAX(ts) FROM commits c WHERE " + " OR ".join(
                ["LOWER(c.email)=?"] * len([k for k in keys if not k.startswith('name:')]) +
                ["LOWER(c.name)=?"] * len([k for k in keys if k.startswith('name:')])) if keys else "SELECT NULL",
            [k for k in keys if not k.startswith("name:")] + [k[5:] for k in keys if k.startswith("name:")]).fetchone()
        if row and row[0]:
            last_touch = datetime.fromtimestamp(row[0], tz=timezone.utc).date().isoformat()
    summary = {"files": len(candidates), "files_in_top5": len(per),
               "top3_current": sum(1 for v in per.values() if strong_cur(v)),
               "top3_built_it": sum(1 for v in per.values() if strong_raw(v)),
               "last_touch": last_touch, "ranks_as_of": ix.rank_now.date().isoformat() if not use_live else when.date().isoformat(),
               "vendored_excluded": not include_vendored}

    # top files
    top_cur = sorted((v for v in per.values() if strong_cur(v)), key=lambda v: -v["score"])[:n_top]
    top_raw = sorted((v for v in per.values() if strong_raw(v)), key=lambda v: -v["raw"])[:n_top]

    # directories: every ancestor level; expertise mass; concentration rule
    files_in = Counter()
    for p in existing:
        d = p
        while "/" in d:
            d = d.rsplit("/", 1)[0]
            files_in[d] += 1
    agg = defaultdict(lambda: {"cur": 0, "built": 0, "mass": 0.0, "files": []})
    for p, v in per.items():
        d = p
        while "/" in d:
            d = d.rsplit("/", 1)[0]
            a = agg[d]
            a["cur"] += strong_cur(v)
            a["built"] += strong_raw(v)
            a["mass"] += (v["score"] if strong_cur(v) else 0.0) + (v["raw"] if strong_raw(v) else 0.0)
            a["files"].append(p)
    rows = {d: a for d, a in agg.items() if a["cur"] + a["built"] >= 2}
    keep = []
    for d, a in rows.items():
        strong = a["cur"] + a["built"]
        children = [c for c in rows if c.rsplit("/", 1)[0] == d and c != d]
        dominated = any(rows[c]["cur"] + rows[c]["built"] >= 0.7 * strong for c in children)
        parent = d.rsplit("/", 1)[0] if "/" in d else None
        pa = rows.get(parent) if parent else None
        cov = strong / files_in[d]
        shadowed = pa is not None and cov < 1.5 * ((pa["cur"] + pa["built"]) / files_in[parent]) and (pa["cur"] + pa["built"]) > strong
        if not dominated and not shadowed:
            reps = sorted((per[p] for p in a["files"] if strong_cur(per[p]) or strong_raw(per[p])),
                          key=lambda v: -((v["score"] if strong_cur(v) else 0.0) + (v["raw"] if strong_raw(v) else 0.0)))[:3]
            keep.append({"dir": d, "files": files_in[d], "top3_current": a["cur"], "top3_built_it": a["built"],
                         "coverage_current": round(a["cur"] / files_in[d], 3), "coverage_built_it": round(a["built"] / files_in[d], 3),
                         "mass": round(a["mass"], 2), "representative": [_file_out(v) for v in reps]})
    keep.sort(key=lambda r: -r["mass"])

    # themes
    stop = _repo_stop(ix)
    df = Counter()
    for p in existing:
        for t in _tokens(p):
            if t not in stop:
                df[t] += 1
    N = max(1, len(existing))
    tf, cnt = Counter(), Counter()
    for p, v in per.items():
        if strong_cur(v) or strong_raw(v):
            w = max(v["score"] if strong_cur(v) else 0.0, v["raw"] if strong_raw(v) else 0.0)
            w *= math.log1p(v["authors"]) if v.get("authors") else 1.0
            for t, tw in _tokens(p).items():
                if t not in stop:
                    tf[t] += w * tw; cnt[t] += 1
    themes = sorted(((t, w * math.log(N / df[t])) for t, w in tf.items() if cnt[t] >= 2 and df[t] / N <= IDF_FLOOR),
                    key=lambda x: -x[1])[:6]

    return {
        "person": {"keys": sorted(keys), "name": next((v["name"] for v in per.values() if v["name"]), None)},
        "summary": summary,
        "themes": [{"token": t, "weight": round(w, 1)} for t, w in themes],
        "top_files": {"current": [_file_out(v) for v in top_cur], "built_it": [_file_out(v) for v in top_raw]},
        "directories": keep[:12],
    }


def _file_out(v: dict) -> dict:
    return {"path": v["path"], "rank_current": v["rank_cur"], "score": round(v["score"], 2),
            "rank_built_it": v["rank_raw"], "raw": round(v["raw"], 2)}


def format_person(rep: dict, query: str, note: str | None) -> str:
    s = rep["summary"]
    L = [f"{rep['person']['name'] or query} — keys: {', '.join(rep['person']['keys'])}"]
    if note:
        L.append(f"  note: {note}")
    L.append(f"  files touched (at HEAD): {s['files']}; top-3 current: {s['top3_current']}; top-3 built_it: {s['top3_built_it']}; "
             f"last touch {s['last_touch']}; ranks as of {s['ranks_as_of']}" + ("; vendored excluded" if s["vendored_excluded"] else ""))
    if rep["themes"]:
        L.append("  themes: " + ", ".join(t["token"] for t in rep["themes"]))
    for label in ("current", "built_it"):
        files = rep["top_files"][label]
        L.append(f"  {label} — {'can answer today' if label == 'current' else 'built it (undecayed)'}:")
        if not files:
            L.append("    (none in the top-3 of any file)")
        for f in files:
            L.append(f"    {f['path']}  #{f['rank_current'] or '-'} cur {f['score']:.2f} · #{f['rank_built_it'] or '-'} raw {f['raw']:.2f}")
    if rep["directories"]:
        L.append("  directories (by expertise mass; top-3 current / built_it of files):")
        for d in rep["directories"]:
            rep_files = ", ".join(r["path"].rsplit("/", 1)[-1] for r in d["representative"])
            L.append(f"    {d['dir']}/  {d['top3_current']}/{d['files']} ({d['coverage_current']:.0%}) · {d['top3_built_it']}/{d['files']} ({d['coverage_built_it']:.0%})  mass {d['mass']:.1f}  e.g. {rep_files}")
    return "\n".join(L)
