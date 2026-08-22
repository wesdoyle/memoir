"""CLI surface: `memoir who`, `memoir audit`."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import typer

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
    return f"{i}. {e.author.name} <{e.author.email}>  score {e.score:.2f}  " + " · ".join(bits)


def _who(root: Path, rel: str, n: int, now: datetime | None) -> tuple[FileHistory, list[Evidence], dict]:
    h = mine_file(root, rel)
    ranked = rank(h, now=now)
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
    h, ranked, div = _who(root, rel, n, _parse_now(now))
    if as_json:
        typer.echo(json.dumps({"path": rel, "paths": h.paths, "experts": [e.to_dict() for e in ranked[:n]],
                               "last_commit": div["last_commit"], "diverges": div["diverges"]}, indent=2))
        return
    if not ranked:
        typer.echo(f"{rel}: no human history")
        return
    typer.echo(f"{rel} — {len(h.human_commits)} knowledge-bearing commits, {len(ranked)} author{'s' if len(ranked) != 1 else ''}"
               + (f", formerly {', '.join(h.paths[1:])}" if len(h.paths) > 1 else ""))
    for i, e in enumerate(ranked[:n], 1):
        typer.echo("  " + _fmt_expert(i, e))
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
    files = subprocess.run(  # ls-tree (not ls-files): works on --no-checkout clones
        ["git", "-C", str(root), "ls-tree", "-r", "--name-only", "-z", "HEAD", "--", rel],
        capture_output=True, text=True, check=True,
    ).stdout.split("\0")
    files = [f for f in files if f]
    when = _parse_now(now)
    bot_last, empty, cases = 0, 0, []
    for f in files:
        h, ranked, div = _who(root, f, top, when)
        if div["last_commit"] is None or not ranked:
            empty += 1
            continue
        if div["last_is_bot"]:
            bot_last += 1
            continue
        last_score = next((e.score for e in ranked if e.author.key == h.last_commit.author.key), 0.0)
        cases.append((f, div, ranked[0], last_score, len(ranked)))
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
