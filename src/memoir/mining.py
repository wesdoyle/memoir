"""Git history -> per-(file, author) raw facts.

Deterministic; git access is via subprocess plumbing only. Identity resolution
honours .mailmap (git applies it to %aN/%aE; co-author trailers are resolved with
`git check-mailmap`). Bot authors and pure merge commits are excluded from facts.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

BOT_RE = re.compile(r"dependabot|renovate|\[bot\]|actions@github", re.I)
COAUTHOR_RE = re.compile(r"^Co-authored-by:\s*(.+?)\s*<([^>]+)>\s*$", re.I | re.M)

_REC = "\x1e"  # record separator between commits
_UNIT = "\x1f"  # field separator within the header


@dataclass(frozen=True)
class Identity:
    name: str
    email: str

    @property
    def key(self) -> str:
        return self.email.lower()

    @property
    def is_bot(self) -> bool:
        return bool(BOT_RE.search(self.name) or BOT_RE.search(self.email))


@dataclass
class Commit:
    sha: str
    author: Identity
    date: datetime  # author date, UTC
    coauthors: list[Identity]
    added: int
    deleted: int
    binary: bool  # numstat reported "-" (no line counts)
    is_merge: bool
    path: str  # path of the file as of this commit (differs across renames)

    @property
    def is_bot(self) -> bool:
        return self.author.is_bot

    @property
    def is_noop(self) -> bool:
        """No content change (pure rename, mode change). Carries no knowledge."""
        return self.added == 0 and self.deleted == 0 and not self.binary


@dataclass
class AuthorFacts:
    author: Identity
    first_authored: bool
    commits: int
    coauthored_count: int
    lines_changed: int
    first_touch: datetime
    last_touch: datetime
    others_commits_since: int  # non-bot, non-merge commits by others after last_touch

    @property
    def name(self) -> str:
        return self.author.name

    @property
    def email(self) -> str:
        return self.author.email


@dataclass
class FileHistory:
    path: str
    paths: list[str]  # all historical paths, current first
    commits: list[Commit]  # newest first; excludes merges, includes bots and no-ops
    authors: list[AuthorFacts]  # excludes bots; no-op commits contribute nothing
    last_commit: Commit | None  # newest non-merge commit, bots included

    @property
    def human_commits(self) -> list[Commit]:
        return [c for c in self.commits if not c.is_bot and not c.is_noop]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def _check_mailmap(repo: Path, idents: set[Identity]) -> dict[Identity, Identity]:
    if not idents:
        return {}
    ordered = sorted(idents, key=lambda i: (i.name, i.email))
    out = _git(repo, "check-mailmap", *[f"{i.name} <{i.email}>" for i in ordered])
    resolved = {}
    for ident, line in zip(ordered, out.splitlines()):
        m = re.match(r"^(.*?)\s*<([^>]*)>$", line.strip())
        resolved[ident] = Identity(m.group(1), m.group(2)) if m else ident
    return resolved


def _parse_log(repo: Path, path: str) -> list[Commit]:
    fmt = _REC + _UNIT.join(["%H", "%aN", "%aE", "%at", "%P", "%B"])
    out = _git(repo, "log", "--follow", "--numstat", f"--format={fmt}", "--", path)
    commits: list[Commit] = []
    raw_coauthors: set[Identity] = set()
    for rec in out.split(_REC)[1:]:
        parts = rec.split(_UNIT, 5)
        sha, name, email, ts, parents, body_and_stat = parts
        body, stat_lines = _split_body_and_numstat(body_and_stat)
        added = deleted = 0
        binary = False
        cur_path = path
        for line in stat_lines:
            a, d, p = line.split("\t", 2)
            binary = binary or a == "-"
            added += int(a) if a != "-" else 0
            deleted += int(d) if d != "-" else 0
            cur_path = _numstat_path(p)
        coauthors = [Identity(n.strip(), e.strip()) for n, e in COAUTHOR_RE.findall(body)]
        raw_coauthors.update(coauthors)
        commits.append(
            Commit(
                sha=sha,
                author=Identity(name, email),
                date=datetime.fromtimestamp(int(ts), tz=timezone.utc),
                coauthors=coauthors,
                added=added,
                deleted=deleted,
                binary=binary,
                is_merge=len(parents.split()) > 1,
                path=cur_path,
            )
        )
    mm = _check_mailmap(repo, raw_coauthors)
    for c in commits:
        c.coauthors = [mm.get(i, i) for i in c.coauthors]
    return commits


def _split_body_and_numstat(text: str) -> tuple[str, list[str]]:
    # %B ends with blank line(s); numstat rows follow. Body may itself contain
    # blank lines, so peel numstat rows off the end rather than splitting on "\n\n".
    lines = text.rstrip("\n").split("\n")
    stat = []
    while lines and re.match(r"^(\d+|-)\t(\d+|-)\t", lines[-1]):
        stat.append(lines.pop())
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines), list(reversed(stat))


def _numstat_path(p: str) -> str:
    # rename forms: "old => new" or "dir/{old => new}/file"
    m = re.match(r"^(.*)\{(.*) => (.*)\}(.*)$", p)
    if m:
        return f"{m.group(1)}{m.group(3)}{m.group(4)}"
    if " => " in p:
        return p.split(" => ", 1)[1]
    return p


def mine_file(repo: str | Path, path: str) -> FileHistory:
    """Mine the full --follow history of `path` (relative to repo root)."""
    repo = Path(repo)
    all_commits = _parse_log(repo, path)
    commits = [c for c in all_commits if not c.is_merge]  # newest first
    human = [c for c in commits if not c.is_bot and not c.is_noop]
    oldest = human[-1] if human else None

    facts: dict[str, AuthorFacts] = {}

    def get(ident: Identity) -> AuthorFacts:
        if ident.key not in facts:
            facts[ident.key] = AuthorFacts(
                author=ident, first_authored=False, commits=0, coauthored_count=0,
                lines_changed=0, first_touch=datetime.max.replace(tzinfo=timezone.utc),
                last_touch=datetime.min.replace(tzinfo=timezone.utc), others_commits_since=0,
            )
        return facts[ident.key]

    for c in human:
        participants = [(c.author, True)] + [(co, False) for co in c.coauthors if not co.is_bot and co.key != c.author.key]
        for ident, primary in participants:
            f = get(ident)
            if primary:
                f.commits += 1
                f.lines_changed += c.added + c.deleted
            else:
                f.coauthored_count += 1
            f.first_touch = min(f.first_touch, c.date)
            f.last_touch = max(f.last_touch, c.date)
    if oldest is not None:
        get(oldest.author).first_authored = True
    for f in facts.values():
        f.others_commits_since = sum(
            1 for c in human if c.date > f.last_touch and c.author.key != f.author.key
        )

    paths: list[str] = []
    for c in commits:
        if c.path not in paths:
            paths.append(c.path)
    if path not in paths:
        paths.insert(0, path)

    return FileHistory(
        path=path,
        paths=paths,
        commits=commits,
        authors=sorted(facts.values(), key=lambda f: (f.author.name, f.author.email)),
        last_commit=commits[0] if commits else None,
    )
