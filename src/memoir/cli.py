"""CLI surface: `memoir who`, `memoir audit`."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import typer

from memoir.index import Index, build_index, default_index_path, open_index
from memoir.mining import FileHistory, mine_file
from memoir.scoring import Evidence, divergence, rank

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
        bits.append(f"{e.others_commits_since} by others since")
    return f"{i}. {e.author.name} <{e.author.email}>  score {e.score:.2f} (raw {e.raw_score:.2f})  " + " · ".join(bits)


def _by_raw(ranked: list[Evidence]) -> list[Evidence]:
    return sorted(ranked, key=lambda e: (-e.raw_score, e.author.name, e.author.email))


class _Source:
    """Chooses between a fresh on-disk index and live mining; announces fallbacks once."""

    def __init__(self, root: Path, live: bool):
        self.root, self.name, self.index = root, "live", None
        if live:
            return
        db = default_index_path(root)
        if not db.exists():
            return
        ix = open_index(db)
        if not ix.is_fresh(root):
            typer.echo(f"memoir: index is stale (built at {ix.head[:10]}, HEAD differs); using live mining. "
                       f"Run `memoir index` to rebuild.", err=True)
            ix.close()
            return
        self.index, self.name = ix, "index"

    def history(self, rel: str) -> FileHistory:
        if self.index is not None:
            if self.index.covers(rel):
                return self.index.history(rel)
            typer.echo(f"memoir: index does not cover {rel} (built for {self.index.pathspec}); using live mining.", err=True)
        return mine_file(self.root, rel)

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
    live: bool = typer.Option(False, "--live", help="Ignore any index; mine git directly"),
) -> None:
    """Ranked experts for a file, with one-line evidence each."""
    root, rel = _resolve(path, repo)
    src = _Source(root, live)
    when = _parse_now(now)
    h, ranked, div = _who(src, rel, n, when)
    dormant, idle = _dormancy(h, when)
    src.close()
    if as_json:
        typer.echo(json.dumps({"path": rel, "paths": h.paths, "experts": [e.to_dict() for e in ranked[:n]],
                               "by_raw_score": [e.to_dict() for e in _by_raw(ranked)[:n]],
                               "ranked_by": "raw_score" if dormant else "score",
                               "dormant": dormant, "dormant_months": round(idle, 1),
                               "last_commit": div["last_commit"], "diverges": div["diverges"],
                               "source": src.name}, indent=2))
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
    live: bool = typer.Option(False, "--live", help="Ignore any index; mine git directly"),
) -> None:
    """Headline stat: % of files whose last committer is NOT in memoir's top-n (how often blame lies)."""
    root, rel = _resolve(directory, repo)
    src = _Source(root, live)
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
