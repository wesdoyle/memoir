"""CLI surface: `memoir who`, `memoir audit`."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import typer

from memoir.api import DORMANT_MONTHS, Source, answer, by_raw, dormancy, fmt_expert, lists_and_flags
from memoir.index import build_index, default_index_path, open_index

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
    src = Source(root, need=rel)
    when = _parse_now(now)
    h, ranked, div = answer(src, rel, n, when)
    dormant, idle = dormancy(h, when)
    src.close()
    if as_json:
        lists, flags = lists_and_flags(h, ranked, n, when)
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
        typer.echo("  " + fmt_expert(i, e))
    raw_top = by_raw(ranked)[:n]
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
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Headline stat: % of files whose last committer is NOT in memoir's top-n (how often blame lies)."""
    root, rel = _resolve(directory, repo)
    src = Source(root, need=rel if rel != "." else None)
    files = subprocess.run(  # ls-tree (not ls-files): works on --no-checkout clones
        ["git", "-C", str(root), "ls-tree", "-r", "--name-only", "-z", "HEAD", "--", rel],
        capture_output=True, text=True, check=True,
    ).stdout.split("\0")
    files = [f for f in files if f]
    when = _parse_now(now)
    bot_last, empty, cases = 0, 0, []
    for f in files:
        h, ranked, div = answer(src, f, top, when)
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
    bad.sort(key=lambda c: -(c[2].score - c[3]))
    if as_json:
        typer.echo(json.dumps({
            "directory": rel, "top": top, "files": len(files), "counted": n,
            "bot_last": bot_last, "no_human_history": empty,
            "diverging": len(bad), "diverging_pct": round(pct, 1),
            "contested": {"files": len(contested), "diverging": len(bad_contested), "diverging_pct": round(cpct, 1)},
            "worst": [{"path": f, "last_commit": div["last_commit"], "last_score": round(last_score, 3),
                       "top": {"name": best.author.name, "email": best.author.email}, "top_score": round(best.score, 3)}
                      for f, div, best, last_score, _ in bad[:worst]],
        }, indent=2))
        return
    typer.echo(f"audit {rel}: {len(files)} tracked files; {bot_last} file(s) last touched by a bot and {empty} without human history excluded")
    typer.echo(f"blame lies: {len(bad)}/{n} files ({pct:.1f}%) — last committer not in memoir top-{top}")
    typer.echo(f"  among contested files (more than {top} authors): {len(bad_contested)}/{len(contested)} ({cpct:.1f}%)")
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


@app.command()
def mcp(
    repo: Path | None = typer.Option(None, "--repo", help="Repository root (default: the current directory's repository)"),
) -> None:
    """Serve the MCP tools over stdio for the repository at --repo (default: the current directory's)."""
    from memoir.mcp_server import make_server

    try:
        root = _toplevel(repo or Path.cwd())
    except typer.BadParameter as e:
        typer.echo(f"memoir mcp: {e}. Run it inside a repository or pass --repo PATH "
                   f"(with uv, use `uv run --project`, not `--directory`, which changes the working directory).", err=True)
        raise typer.Exit(code=2)
    typer.echo(f"memoir mcp: serving {root}", err=True)
    make_server(root).run()


@app.command()
def identities(
    repo: Path | None = typer.Option(None, "--repo"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Suggest .mailmap lines for split identities (same name / noreply / spellings / handles). Nothing is written."""
    from memoir.identities import format_mailmap, suggest_mailmap

    root, _ = _resolve(".", repo)
    src = Source(root)
    try:
        out = suggest_mailmap(src.index)
    finally:
        src.close()
    if as_json:
        typer.echo(json.dumps({k: [{"mailmap": l, "commits": c} for l, c in v] for k, v in out.items()}, indent=2))
    else:
        typer.echo(format_mailmap(out))


@app.command()
def person(
    who: str = typer.Argument(..., help="Name or email (substring; exact email wins)"),
    repo: Path | None = typer.Option(None, "--repo"),
    as_json: bool = typer.Option(False, "--json"),
    now: str | None = typer.Option(None, "--now", help="Reference date YYYY-MM-DD; ranks are recomputed live if it is outside the index's window"),
    include_vendored: bool = typer.Option(False, "--include-vendored", help="Count vendored trees (deps/, 3rdparty/, vendor/ ...)"),
    top: int = typer.Option(8, "--top", help="Files to list per answer"),
) -> None:
    """What does this person know: top files, directories and themes, for `current` and `built_it`."""
    from memoir.person import format_person, person_report, resolve_person

    root, _ = _resolve(".", repo)
    src = Source(root)
    try:
        keys, note = resolve_person(src.index, who)
        if not keys:
            typer.echo(f"memoir: {note}", err=True)
            raise typer.Exit(code=1)
        rep = person_report(src.index, keys, now=_parse_now(now), n_top=top, include_vendored=include_vendored)
    finally:
        src.close()
    if note:
        rep["person"]["note"] = note
    typer.echo(json.dumps(rep, indent=2) if as_json else format_person(rep, who, note))


@app.command()
def experts(
    dir: str | None = typer.Option(None, "--dir", help="Files under this directory"),
    glob: str | None = typer.Option(None, "--glob", help="Files matching this glob (full path or file name)"),
    match: list[str] = typer.Option([], "--match", help="Path-token word (repeatable; any word matches)"),
    prefix: bool = typer.Option(False, "--prefix", help="Match token prefixes (auth -> authc, authz ...)"),
    files: str | None = typer.Option(None, "--files", help="File list: a path, or - for stdin (one per line; e.g. a diff's files)"),
    repo: Path | None = typer.Option(None, "--repo"),
    top: int = typer.Option(10, "--top"),
    as_json: bool = typer.Option(False, "--json"),
    now: str | None = typer.Option(None, "--now"),
    include_vendored: bool = typer.Option(False, "--include-vendored"),
) -> None:
    """Who has the most expertise across a set of files (a directory, a glob, a topic word, or a file list)."""
    import sys
    from memoir.experts import experts_report, format_experts, select_files

    root, _ = _resolve(".", repo)
    listed = None
    if files is not None:
        listed = (sys.stdin.read() if files == "-" else Path(files).read_text()).splitlines()
    src = Source(root)
    try:
        paths, desc = select_files(src.index, dir=dir, glob=glob, match=list(match) or None, prefix=prefix,
                                   files=listed, include_vendored=include_vendored)
        if not paths:
            typer.echo(f"memoir: no files selected ({desc})", err=True)
            raise typer.Exit(code=1)
        rep = experts_report(src.index, paths, n=top, now=_parse_now(now))
    finally:
        src.close()
    rep["selection"]["selector"] = desc
    typer.echo(json.dumps(rep, indent=2) if as_json else format_experts(rep, desc))
