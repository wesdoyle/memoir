"""Regression harness: a fixed report from fixed inputs, diffable against a saved run.

    uv run python eval/regress.py run <name> [--set key=value ...]   # -> eval/regress/<name>.{json,md}
    uv run python eval/regress.py diff <base> <name>                 # movement report (markdown, stdout)

`--set` overrides fields of memoir.scoring.Weights (e.g. --set half_life_months=36 --set breadth_k=10).
Everything is read from the on-disk indexes under eval/repos/<repo>/.git/memoir/index.sqlite;
`now` is pinned to 2026-08-21 so the report is reproducible. Sections:

  audit       the 10 P4 directories at HL=18 / HL=60 / raw: all-files and contested divergence
  samples     top-1 / top-3 on random.Random(42).sample(100) files per repo (for rank-shift diffs)
  canaries    named cases fixed before any scoring change; regression tests, not targets
  regression  rankings judged correct; must not move
  roster      Valkey MAINTAINERS overlap on the 30 busiest src/*.c files (top-1 listed, top-3 slots)
"""

from __future__ import annotations

import json
import random
import re
import subprocess
import sys
from collections import Counter
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path

from memoir.index import default_index_path, open_index
from memoir.scoring import Weights, _first_earns, divergence, rank

ROOT = Path(__file__).resolve().parent.parent
REPOS = ROOT / "eval" / "repos"
OUT = ROOT / "eval" / "regress"
NOW = datetime(2026, 8, 21, tzinfo=timezone.utc)
SEED, SAMPLE_N, TOP = 42, 100, 3
ALL_REPOS = ["valkey", "opencv", "flink", "elasticsearch", "vscode"]

DIRS = [
    ("valkey", "src"),
    ("opencv", "modules/core/src"),
    ("opencv", "modules/imgproc/src"),
    ("flink", "flink-runtime/src/main/java/org/apache/flink/runtime/checkpoint"),
    ("flink", "flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster"),
    ("flink", "flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph"),
    ("elasticsearch", "server/src/main/java/org/elasticsearch/cluster"),
    ("elasticsearch", "server/src/main/java/org/elasticsearch/index/engine"),
    ("vscode", "src/vs/editor/common"),
    ("vscode", "src/vs/base/common"),
]

ES = "server/src/main/java/org/elasticsearch/"
# (label, repo, path, author display name) -> rank of that author
CANARIES = [
    ("antirez on valkey server.c", "valkey", "src/server.c", "antirez"),
    ("Till Rohrmann on flink JobMaster.java", "flink", "flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster/JobMaster.java", "Till Rohrmann"),
    ("Shay Banon on ES IndexMetadata.java", "elasticsearch", ES + "cluster/metadata/IndexMetadata.java", "Shay Banon"),
    ("Shay Banon on ES InternalEngine.java", "elasticsearch", ES + "index/engine/InternalEngine.java", "Shay Banon"),
    ("Shay Banon on ES SearchService.java", "elasticsearch", ES + "search/SearchService.java", "Shay Banon"),
    ("Shay Banon on ES Node.java", "elasticsearch", ES + "node/Node.java", "Shay Banon"),
    ("Ran Shidlansik (1,293-line commit) on valkey t_zset.c", "valkey", "src/t_zset.c", "Ran Shidlansik"),
]
REGRESSION = [
    ("Alex Dima on vscode textModel.ts", "vscode", "src/vs/editor/common/model/textModel.ts", "Alex Dima"),
    ("Johannes Rieken on vscode event.ts", "vscode", "src/vs/base/common/event.ts", "Johannes Rieken"),
    ("David Turner on ES Node.java", "elasticsearch", ES + "node/Node.java", "David Turner"),
    ("Ryan Ernst on ES Node.java", "elasticsearch", ES + "node/Node.java", "Ryan Ernst"),
    ("Vadim Pisarevsky on opencv matrix.cpp", "opencv", "modules/core/src/matrix.cpp", "Vadim Pisarevsky"),
    ("Madelyn Olson on valkey config.c", "valkey", "src/config.c", "Madelyn Olson"),
]
SWEEP_AUTHOR = "Josh Soref"
IMPORTER = "Erich Gamma"
VSCODE_DIRS = [d for r, d in DIRS if r == "vscode"]


def sh(repo: str, *args: str) -> str:
    return subprocess.run(["git", "-C", str(REPOS / repo), *args], check=True, capture_output=True, text=True).stdout


def tracked(repo: str, d: str = ".") -> list[str]:
    return [f for f in sh(repo, "ls-tree", "-r", "--name-only", "-z", "HEAD", "--", d).split("\0") if f]


def parse_overrides(argv: list[str]) -> dict:
    kw = {}
    names = {f.name: f.type for f in fields(Weights)}
    i = 0
    while i < len(argv):
        if argv[i] == "--set":
            k, v = argv[i + 1].split("=", 1)
            if k not in names:
                raise SystemExit(f"unknown Weights field {k}; known: {sorted(names)}")
            try:
                kw[k] = int(v)
            except ValueError:
                try:
                    kw[k] = float(v)
                except ValueError:
                    kw[k] = v
            i += 2
        else:
            raise SystemExit(f"unexpected arg {argv[i]}")
    return kw


def _rank_of(ranked, name: str):
    for i, e in enumerate(ranked, 1):
        if e.author.name == name:
            return i
    return None


def busiest_valkey_c(ix, n=30) -> list[str]:
    existing = set(tracked("valkey", "src"))
    rows = ix.con.execute("SELECT path, COUNT(*) c FROM files WHERE path LIKE 'src/%.c' GROUP BY path ORDER BY c DESC, path").fetchall()
    return [p for p, _ in rows if p in existing][:n]


def valkey_roster() -> set[str]:
    mm = sh("valkey", "show", "HEAD:MAINTAINERS.md")
    names = set()
    for line in mm.splitlines():
        m = re.match(r"^\|\s*([A-Za-z][^|]+?)\s*\|\s*@\S+\s*\|", line)
        if m and m.group(1) not in ("Maintainer", "Committer", "Name"):
            names.add(m.group(1).strip())
    return names


def is_listed(name: str, roster: set[str]) -> bool:
    return any(name.split()[0].lower() == m.split()[0].lower() for m in roster)


def run(name: str, overrides: dict) -> dict:
    base = Weights(**overrides)
    regimes = {
        "hl18": base,
        "hl60": Weights(**{**overrides, "half_life_months": 60.0}),
        "raw": Weights(**{**overrides, "half_life_months": 1e9}),
    }
    if "half_life_months" in overrides:
        regimes["hl18"] = base  # the candidate's own half-life; label kept for column stability
    report = {"name": name, "overrides": overrides, "now": NOW.date().isoformat(), "seed": SEED,
              "audit": {}, "samples": {}, "canaries": {}, "regression": {}, "roster": {}}
    idx = {r: open_index(default_index_path(REPOS / r)) for r in ALL_REPOS}
    try:
        # audit
        for repo, d in DIRS:
            ix = idx[repo]
            stats = {k: {"n": 0, "bad": 0, "contested": 0, "bad_contested": 0} for k in regimes}
            for f in tracked(repo, d):
                h = ix.history(f)
                if not h.authors or h.last_commit is None or h.last_commit.is_bot:
                    continue
                for k, w in regimes.items():
                    r = rank(h, now=NOW, w=w)
                    dv = divergence(h, r, TOP)["diverges"]
                    s = stats[k]
                    s["n"] += 1
                    s["bad"] += dv
                    if len(r) > TOP:
                        s["contested"] += 1
                        s["bad_contested"] += dv
            report["audit"][f"{repo}:{d}"] = stats
        # samples
        for repo in ALL_REPOS:
            files = random.Random(SEED).sample(tracked(repo), SAMPLE_N)
            per = {}
            for f in files:
                r = rank(idx[repo].history(f), now=NOW, w=base)
                per[f] = {"top1": r[0].author.name if r else None, "top3": [e.author.name for e in r[:TOP]]}
            report["samples"][repo] = per
        # canaries
        for label, repo, path, author in CANARIES:
            report["canaries"][label] = _rank_of(rank(idx[repo].history(path), now=NOW, w=base), author)
        busiest = busiest_valkey_c(idx["valkey"])
        sweep = 0
        for f in busiest:
            r = rank(idx["valkey"].history(f), now=NOW, w=base)
            sweep += SWEEP_AUTHOR in [e.author.name for e in r[:TOP]]
        report["canaries"][f"{SWEEP_AUTHOR} in top-3 of valkey's 30 busiest src/*.c"] = sweep
        gamma = 0
        n_vs = 0
        for d in VSCODE_DIRS:
            for f in tracked("vscode", d):
                h = idx["vscode"].history(f)
                n_vs += 1
                gamma += any(a.first_authored and a.name == IMPORTER and _first_earns(a, base) for a in h.authors)
        report["canaries"][f"{IMPORTER} earns first_authored credit in vscode audited dirs (of {n_vs})"] = gamma
        credited = n_creators = 0
        for repo, d in DIRS:
            for f in tracked(repo, d):
                h = idx[repo].history(f)
                c = next((a for a in h.authors if a.first_authored), None)
                if c is not None:
                    n_creators += 1
                    credited += _first_earns(c, base)
        report["canaries"][f"files in the 10 P4 dirs whose creator earns first_authored credit (of {n_creators})"] = credited
        # regression
        for label, repo, path, author in REGRESSION:
            report["regression"][label] = _rank_of(rank(idx[repo].history(path), now=NOW, w=base), author)
        # roster
        roster = valkey_roster()
        top1 = slots = 0
        for f in busiest:
            r = rank(idx["valkey"].history(f), now=NOW, w=base)
            names = [e.author.name for e in r[:TOP]]
            top1 += bool(names) and is_listed(names[0], roster)
            slots += sum(is_listed(n, roster) for n in names)
        report["roster"] = {"top1_listed": top1, "files": len(busiest), "top3_slots_listed": slots, "slots": TOP * len(busiest)}
    finally:
        for ix in idx.values():
            ix.close()
    return report


def pct(a, b):
    return f"{a}/{b} ({100*a/b:.1f}%)" if b else "–"


def to_md(rep: dict) -> str:
    L = [f"# regress: {rep['name']}", "", f"overrides: `{rep['overrides'] or 'none'}` · now {rep['now']} · seed {rep['seed']}", ""]
    L += ["## audit (last committer outside top-3)", "", "| directory | HL18 all | HL18 contested | HL60 all | HL60 contested | raw all | raw contested |", "|---|---|---|---|---|---|---|"]
    for d, st in rep["audit"].items():
        cells = []
        for k in ("hl18", "hl60", "raw"):
            s = st[k]
            cells += [pct(s["bad"], s["n"]), pct(s["bad_contested"], s["contested"])]
        L.append(f"| {d} | " + " | ".join(cells) + " |")
    L += ["", "## canaries", "", "| case | value |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in rep["canaries"].items()]
    L += ["", "## regression (must not move)", "", "| case | rank |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in rep["regression"].items()]
    r = rep["roster"]
    L += ["", "## valkey MAINTAINERS overlap (30 busiest src/*.c)", "", f"top-1 listed {r['top1_listed']}/{r['files']} · top-3 slots listed {r['top3_slots_listed']}/{r['slots']}", ""]
    L += ["## samples", "", "| repo | files | top-1 sample |", "|---|---|---|"]
    for repo, per in rep["samples"].items():
        c = Counter(v["top1"] for v in per.values())
        L.append(f"| {repo} | {len(per)} | " + ", ".join(f"{n} ×{k}" for n, k in c.most_common(5)) + " |")
    return "\n".join(L) + "\n"


def diff(base: dict, new: dict) -> str:
    L = [f"# regress diff: {base['name']} -> {new['name']}", "", f"overrides: `{base['overrides'] or 'none'}` -> `{new['overrides'] or 'none'}`", ""]
    L += ["## audit: divergence before -> after (all files · contested)", "", "| directory | HL18 | HL60 | raw |", "|---|---|---|---|"]
    for d in base["audit"]:
        cells = []
        for k in ("hl18", "hl60", "raw"):
            a, b = base["audit"][d][k], new["audit"][d][k]
            cells.append(f"{a['bad']}→{b['bad']}/{b['n']} · {a['bad_contested']}→{b['bad_contested']}/{b['contested']}")
        L.append(f"| {d} | " + " | ".join(cells) + " |")
    L += ["", "## canaries (regression tests, not targets)", "", "| case | before | after | moved |", "|---|---|---|---|"]
    for k in base["canaries"]:
        a, b = base["canaries"][k], new["canaries"].get(k)
        L.append(f"| {k} | {a} | {b} | {'' if a == b else '**yes**'} |")
    L += ["", "## regression set (must not move)", "", "| case | before | after | moved |", "|---|---|---|---|"]
    for k in base["regression"]:
        a, b = base["regression"][k], new["regression"].get(k)
        L.append(f"| {k} | {a} | {b} | {'' if a == b else '**MOVED**'} |")
    ra, rb = base["roster"], new["roster"]
    L += ["", "## valkey MAINTAINERS overlap", "", f"top-1 listed {ra['top1_listed']}→{rb['top1_listed']}/{rb['files']} · top-3 slots {ra['top3_slots_listed']}→{rb['top3_slots_listed']}/{rb['slots']}", ""]
    L += ["## rank shift on seeded samples", "", "| repo | top-1 changed | top-3 set changed | entered top-3 (most) | left top-3 (most) |", "|---|---|---|---|---|"]
    for repo in base["samples"]:
        a, b = base["samples"][repo], new["samples"][repo]
        t1 = t3 = 0
        entered, left = Counter(), Counter()
        for f in a:
            if f not in b:
                continue
            t1 += a[f]["top1"] != b[f]["top1"]
            sa, sb = set(a[f]["top3"]), set(b[f]["top3"])
            if sa != sb:
                t3 += 1
                entered.update(sb - sa)
                left.update(sa - sb)
        fmt = lambda c: ", ".join(f"{n} ×{k}" for n, k in c.most_common(4)) or "–"
        L.append(f"| {repo} | {t1}/{len(a)} | {t3}/{len(a)} | {fmt(entered)} | {fmt(left)} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "run":
        name = sys.argv[2]
        rep = run(name, parse_overrides(sys.argv[3:]))
        (OUT / f"{name}.json").write_text(json.dumps(rep, indent=1, sort_keys=True))
        (OUT / f"{name}.md").write_text(to_md(rep))
        print(to_md(rep))
    elif cmd == "diff":
        base = json.loads((OUT / f"{sys.argv[2]}.json").read_text())
        new = json.loads((OUT / f"{sys.argv[3]}.json").read_text())
        print(diff(base, new))
    else:
        raise SystemExit(__doc__)
