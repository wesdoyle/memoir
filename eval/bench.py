"""Performance baseline for memoir. Measurement only: no caching, no persistence.

Usage (from repo root, clones under eval/repos/):
    uv run python eval/bench.py files              # per-file who() cost split, all repos
    uv run python eval/bench.py git                # git-level micro-benchmarks per file
    uv run python eval/bench.py dir <repo> <dir>   # per-file distribution over a directory
    uv run python eval/bench.py startup            # CLI process startup

Timing is wall-clock (perf_counter), median of REPEATS for the per-file sections. The
git subprocess time is measured by wrapping memoir.mining._git from the outside; the
production code is not instrumented.
"""

from __future__ import annotations

import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import memoir.mining as mining
from memoir.mining import mine_file
from memoir.scoring import rank

ROOT = Path(__file__).resolve().parent.parent
REPOS = ROOT / "eval" / "repos"
REPEATS = 3
NOW = datetime(2026, 8, 21, tzinfo=timezone.utc)

# (repo, path) — light / medium / heavy history per repo
FILES = [
    ("valkey", "src/lzf_c.c"),
    ("valkey", "src/t_zset.c"),
    ("valkey", "src/server.c"),
    ("opencv", "modules/core/src/has_non_zero.simd.hpp"),
    ("opencv", "modules/imgproc/src/imgwarp.cpp"),
    ("opencv", "modules/core/src/matrix.cpp"),
    ("flink", "flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster/JobMasterId.java"),
    ("flink", "flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster/JobMaster.java"),
    ("flink", "flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph/ExecutionGraph.java"),
    ("elasticsearch", "server/src/main/java/org/elasticsearch/index/engine/EngineException.java"),
    ("elasticsearch", "server/src/main/java/org/elasticsearch/cluster/metadata/IndexMetadata.java"),
    ("elasticsearch", "server/src/main/java/org/elasticsearch/index/engine/InternalEngine.java"),
    ("vscode", "src/vs/base/common/lazy.ts"),
    ("vscode", "src/vs/editor/common/model/textModel.ts"),
    ("vscode", "src/vs/workbench/api/common/extHost.api.impl.ts"),
]


class GitTimer:
    """Wraps mining._git to attribute wall time to git subprocesses by subcommand."""

    def __init__(self):
        self.by_cmd: dict[str, float] = {}
        self.calls = 0
        self._orig = mining._git

    def __enter__(self):
        def timed(repo, *args):
            t = time.perf_counter()
            try:
                return self._orig(repo, *args)
            finally:
                self.by_cmd[args[0]] = self.by_cmd.get(args[0], 0.0) + time.perf_counter() - t
                self.calls += 1
        mining._git = timed
        return self

    def __exit__(self, *_exc):
        mining._git = self._orig

    @property
    def total(self):
        return sum(self.by_cmd.values())


def sh(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def median_of(fn, n=REPEATS):
    xs = [fn() for _ in range(n)]
    return statistics.median(xs)


def bench_files():
    print("| repo | file | commits | authors | total ms | git log | check-mailmap | parse+facts | score | git % |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for repo, path in FILES:
        r = REPOS / repo
        rows = []
        h = None
        for _ in range(REPEATS):
            with GitTimer() as gt:
                t0 = time.perf_counter()
                h = mine_file(r, path)
                t1 = time.perf_counter()
                rank(h, now=NOW)
                t2 = time.perf_counter()
            rows.append((t1 - t0, gt.by_cmd.get("log", 0.0), gt.by_cmd.get("check-mailmap", 0.0), t2 - t1))
        rows.sort(key=lambda x: x[0])
        mine_t, log_t, mm_t, score_t = rows[len(rows) // 2]
        total = mine_t + score_t
        parse = mine_t - log_t - mm_t
        assert h is not None
        print(f"| {repo} | `{path.split('/')[-1]}` | {len(h.commits)} | {len(h.authors)} | {total*1000:.0f} | "
              f"{log_t*1000:.0f} | {mm_t*1000:.0f} | {parse*1000:.0f} | {score_t*1000:.1f} | {100*(log_t+mm_t)/total:.0f}% |")


def bench_git():
    print("| repo | file | commits | log --follow --numstat | log --numstat (no follow) | log --follow (no numstat) | log (plain) | rev-list --count |")
    print("|---|---|---|---|---|---|---|---|")
    fmt = "--format=%H%x1f%aN%x1f%aE%x1f%at%x1f%P%x1f%B"
    variants = [
        ("follow+numstat", ["log", "--follow", "--numstat", fmt, "--"]),
        ("numstat", ["log", "--numstat", fmt, "--"]),
        ("follow", ["log", "--follow", fmt, "--"]),
        ("plain", ["log", fmt, "--"]),
        ("count", ["rev-list", "--count", "HEAD", "--"]),
    ]
    for repo, path in FILES:
        r = REPOS / repo
        n = sh(r, "rev-list", "--count", "HEAD", "--", path).strip()
        cells = []
        for _, args in variants:
            t = median_of(lambda: _timed(lambda: sh(r, *args, path)))
            cells.append(f"{t*1000:.0f}")
        print(f"| {repo} | `{path.split('/')[-1]}` | {n} | " + " | ".join(cells) + " |")


def _timed(fn):
    t = time.perf_counter()
    fn()
    return time.perf_counter() - t


def bench_dir(repo: str, d: str):
    r = REPOS / repo
    files = [f for f in sh(r, "ls-tree", "-r", "--name-only", "HEAD", "--", d).split("\n") if f]
    samples = []  # (seconds, commits, authors)
    t_all = time.perf_counter()
    for f in files:
        t = time.perf_counter()
        h = mine_file(r, f)
        rank(h, now=NOW)
        samples.append((time.perf_counter() - t, len(h.commits), len(h.authors)))
    wall = time.perf_counter() - t_all
    ts = sorted(s[0] for s in samples)
    q = lambda p: ts[min(len(ts) - 1, int(p * len(ts)))]
    print(f"### {repo} `{d}` — {len(files)} files, wall {wall:.1f} s, {len(files)/wall:.1f} files/s")
    print(f"- per file: min {ts[0]*1000:.0f} ms · p50 {q(0.5)*1000:.0f} · p90 {q(0.9)*1000:.0f} · p95 {q(0.95)*1000:.0f} · max {ts[-1]*1000:.0f} · mean {statistics.mean(ts)*1000:.0f}")
    # cost vs history depth: bucket by commit count
    buckets = [(0, 5), (5, 20), (20, 100), (100, 500), (500, 10**9)]
    parts = []
    for lo, hi in buckets:
        b = [s[0] for s in samples if lo <= s[1] < hi]
        if b:
            parts.append(f"{lo}-{hi if hi < 10**9 else '∞'} commits: n={len(b)}, median {statistics.median(b)*1000:.0f} ms")
    print("- by history depth: " + "; ".join(parts))
    big = sorted(samples, key=lambda s: -s[0])[:3]
    print("- slowest: " + "; ".join(f"{s[0]*1000:.0f} ms ({s[1]} commits, {s[2]} authors)" for s in big))
    print()


def bench_startup():
    env_cmds = [
        ("uv run memoir --help", ["uv", "run", "memoir", "--help"]),
        (".venv/bin/memoir --help", [str(ROOT / ".venv/bin/memoir"), "--help"]),
        ("python -c 'import memoir.cli'", [str(ROOT / ".venv/bin/python"), "-c", "import memoir.cli"]),
        ("python -c 'import memoir.mining'", [str(ROOT / ".venv/bin/python"), "-c", "import memoir.mining"]),
        ("git --version", ["git", "--version"]),
    ]
    print("| command | median ms (of 5) |")
    print("|---|---|")
    for label, cmd in env_cmds:
        t = median_of(lambda: _timed(lambda: subprocess.run(cmd, cwd=ROOT, capture_output=True, check=True)), n=5)
        print(f"| `{label}` | {t*1000:.0f} |")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "files"
    if what == "files":
        bench_files()
    elif what == "git":
        bench_git()
    elif what == "dir":
        bench_dir(sys.argv[2], sys.argv[3])
    elif what == "startup":
        bench_startup()
    else:
        raise SystemExit(__doc__)
