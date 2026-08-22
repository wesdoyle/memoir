"""CLI surface: `memoir who`, `memoir audit`."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import typer

from memoir.index import Index, build_index, default_index_path, open_index
from memoir.mining import FileHistory
from memoir.scoring import Evidence, Weights, divergence, rank

app = typer.Typer(no_args_is_help=True, help="Find who most likely holds the mental model of a file.")


def _toplevel(start: Path) -> Path:
    out = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if out.returncode != 0:
        raise typer.BadParameter(f"not inside a git repository: {start}")
    return Path(out.stdout.strip())


def _resolve(path: str, repo: Path | None) -> tuple[Path, str]:
    """Return (repo_root, path relative to root)."""
    if repo is not None:
        root = _toplevel(repo)
        return root, path
    p = Path(path).resolve()
    root = _toplevel(p if p.is_dir() else p.parent)
    return root, str(p.relative_to(root)) if p != root else "."


def _parse_now(now: str | None) -> datetime | None:
    return datetime.fromisoformat(now).replace(tzinfo=timezone.utc) if now else None


def _fmt_expert(i: int, e: Evidence) -> str:
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


def _by_raw(ranked: list[Evidence]) -> list[Evidence]:
    return sorted(ranked, key=lambda e: (-e.raw_score, e.author.name, e.author.email))


class _Source:
    """The on-disk index for a repository; built or refreshed on demand with a one-line notice."""

    def __init__(self, root: Path, need: str | None = None):
        self.root = root
        self.db = default_index_path(root)
        self.index: Index | None = None
        reason = None
        if not self.db.exists():
            reason = "no index yet"
        else:
            ix = open_index(self.db)
            if not ix.is_fresh(root):
                reason = f"index is stale (built at {ix.head[:10]}, HEAD differs)"
            elif need is not None and not ix.covers(need):
                reason = f"index covers only {ix.pathspec}"
            if reason:
                ix.close()
            else:
                self.index = ix
        if reason:
            typer.echo(f"memoir: {reason}; building index for {root} ...", err=True)
            build_index(root, self.db)
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


def _dormancy(h: FileHistory, now: datetime | None) -> tuple[bool, float]:
    """(dormant, months since the last knowledge-bearing human touch)."""
    from memoir.scoring import months_between
    now = now or datetime.now(tz=timezone.utc)
    if not h.authors:
        return False, 0.0
    idle = min(months_between(a.last_touch, now) for a in h.authors)
    return idle > DORMANT_MONTHS, idle


SWEEP_BREADTH = 50  # a last commit touching more files than this is flagged as a sweep
STABILITY_HALF_LIVES = {"12": 12.0, "18": 18.0, "36": 36.0, "inf": 1e9}


def _lists_and_flags(h: FileHistory, ranked: list[Evidence], n: int, now: datetime | None) -> tuple[dict, dict]:
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
    dormant, idle = _dormancy(h, now)
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
        "built_it": [e.to_dict() for e in _by_raw(ranked)[:n]],  # raw: deepest accumulated knowledge
        "recent": recent,                                      # pure recency baseline: what blame/log says
    }
    return lists, flags


def _who(src: _Source, rel: str, n: int, now: datetime | None) -> tuple[FileHistory, list[Evidence], dict]:
    """Rank; on a dormant file the decayed order is noise, so rank by raw score instead."""
    h = src.history(rel)
    ranked = rank(h, now=now)
    dormant, _ = _dormancy(h, now)
    if dormant:
        ranked = _by_raw(ranked)
    return h, ranked, divergence(h, ranked, n)


@app.command()
def who(
    path: str = typer.Argument(..., help="File path (relative to cwd, or to --repo if given)"),
    n: int = typer.Option(3, "-n", help="Number of experts to show"),
    repo: Path | None = typer.Option(None, "--repo", help="Repository root (default: discover from path)"),
    as_json: bool = typer.Option(False, "--json", help="Emit structured JSON"),
    now: str | None = typer.Option(None, "--now", help="Reference date YYYY-MM-DD (default: today); for reproducible output"),
) -> None:
    """Ranked experts for a file, with one-line evidence each."""
    root, rel = _resolve(path, repo)
    src = _Source(root, need=rel)
    when = _parse_now(now)
    h, ranked, div = _who(src, rel, n, when)
    dormant, idle = _dormancy(h, when)
    src.close()
    if as_json:
        lists, flags = _lists_and_flags(h, ranked, n, when)
        typer.echo(json.dumps({"path": rel, "paths": h.paths, "experts": [e.to_dict() for e in ranked[:n]],
                               "by_raw_score": lists["built_it"],
                               "ranked_by": "raw_score" if dormant else "score",
                               "dormant": dormant, "dormant_months": round(idle, 1),
                               "lists": lists, "flags": flags,
                               "last_commit": div["last_commit"], "diverges": div["diverges"],
                               "source": src.name, "index_head": src.head}, indent=2))
        return
    if not ranked:
        typer.echo(f"{rel}: no human history")
        return
    typer.echo(f"{rel} — {len(h.human_commits)} knowledge-bearing commits, {len(ranked)} author{'s' if len(ranked) != 1 else ''}"
               + (f", formerly {', '.join(h.paths[1:])}" if len(h.paths) > 1 else ""))
    if dormant:
        typer.echo(f"  dormant: no knowledge-bearing change for {idle:.0f} months (> {DORMANT_MONTHS:.0f}); "
                   f"decayed scores are all near zero, so this list is ordered by raw score (who built it)")
    for i, e in enumerate(ranked[:n], 1):
        typer.echo("  " + _fmt_expert(i, e))
    raw_top = _by_raw(ranked)[:n]
    if not dormant and {e.author.key for e in raw_top} != {e.author.key for e in ranked[:n]}:
        typer.echo("  by raw score (before time decay): "
                   + " · ".join(f"{e.author.name} {e.raw_score:.2f} (last {e.last_touch})" for e in raw_top))
    lc = div["last_commit"]
    tag = "bot" if div["last_is_bot"] else (f"rank {div['rank_of_last']}" if div["rank_of_last"] else "no expertise record")
    typer.echo(f"  last commit: {lc['author']['name']} {lc['date']} ({tag})"
               + ("  <- NOT in memoir top-%d" % n if div["diverges"] else ""))


@app.command()
def audit(
    directory: str = typer.Argument(".", help="Directory to audit (relative to cwd, or to --repo)"),
    top: int = typer.Option(3, "--top", help="Top-n experts to compare the last committer against"),
    repo: Path | None = typer.Option(None, "--repo"),
    worst: int = typer.Option(10, "--worst", help="How many worst cases to list"),
    now: str | None = typer.Option(None, "--now", help="Reference date YYYY-MM-DD"),
) -> None:
    """Headline stat: % of files whose last committer is NOT in memoir's top-n (how often blame lies)."""
    root, rel = _resolve(directory, repo)
    src = _Source(root, need=rel if rel != "." else None)
    files = subprocess.run(  # ls-tree (not ls-files): works on --no-checkout clones
        ["git", "-C", str(root), "ls-tree", "-r", "--name-only", "-z", "HEAD", "--", rel],
        capture_output=True, text=True, check=True,
    ).stdout.split("\0")
    files = [f for f in files if f]
    when = _parse_now(now)
    bot_last, empty, cases = 0, 0, []
    for f in files:
        h, ranked, div = _who(src, f, top, when)
        if div["last_commit"] is None or not ranked:
            empty += 1
            continue
        if div["last_is_bot"]:
            bot_last += 1
            continue
        last_score = next((e.score for e in ranked if e.author.key == h.last_commit.author.key), 0.0)
        cases.append((f, div, ranked[0], last_score, len(ranked)))
    src.close()
    n = len(cases)
    bad = [c for c in cases if c[1]["diverges"]]
    pct = 100.0 * len(bad) / n if n else 0.0
    contested = [c for c in cases if c[4] > top]  # top-n membership is non-trivial only here
    bad_contested = [c for c in contested if c[1]["diverges"]]
    cpct = 100.0 * len(bad_contested) / len(contested) if contested else 0.0
    typer.echo(f"audit {rel}: {len(files)} tracked files; {bot_last} file(s) last touched by a bot and {empty} without human history excluded")
    typer.echo(f"blame lies: {len(bad)}/{n} files ({pct:.1f}%) — last committer not in memoir top-{top}")
    typer.echo(f"  among contested files (more than {top} authors): {len(bad_contested)}/{len(contested)} ({cpct:.1f}%)")
    bad.sort(key=lambda c: -(c[2].score - c[3]))
    if bad:
        typer.echo(f"worst cases (largest gap between top expert and last committer):")
        for f, div, best, last_score, _ in bad[:worst]:
            lc = div["last_commit"]
            typer.echo(f"  {f}: last {lc['author']['name']} {lc['date']} (score {last_score:.2f}) vs top {best.author.name} (score {best.score:.2f})")


@app.command()
def index(
    directory: str = typer.Argument(None, help="Limit the index to this directory (default: whole repository)"),
    repo: Path | None = typer.Option(None, "--repo"),
    path: Path | None = typer.Option(None, "--path", help="Index file (default: <git-dir>/memoir/index.sqlite)"),
) -> None:
    """Walk the history once and persist it; `who` and `audit` use it while HEAD is unchanged."""
    import time

    root, rel = _resolve(directory or ".", repo)
    pathspec = None if rel in (".", "") else rel
    db = path or default_index_path(root)
    t = time.perf_counter()
    build_index(root, db, pathspec=pathspec)
    dt = time.perf_counter() - t
    with open_index(db) as ix:
        size = db.stat().st_size / 1e6
        typer.echo(f"indexed {ix.meta['commits']} commits" + (f" under {pathspec}" if pathspec else "")
                   + f" at {ix.head[:10]} in {dt:.1f} s -> {db} ({size:.1f} MB)")
