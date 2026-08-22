"""Git history -> per-(file, author) raw facts.

Deterministic; git access is via subprocess plumbing only. Identity resolution
honours .mailmap (git applies it to %aN/%aE; co-author trailers are resolved with
`git check-mailmap`). Bot authors and pure merge commits are excluded from facts.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

BOT_RE = re.compile(r"dependabot|renovate|\[bot\]|actions@github", re.I)  # name or email
# Name-only patterns. "bot" must be its own token or a suffix after a separator, or one of
# the known compounds (buildbot, pushbot): "Talbot", "cccabot", "Abbott" are people.
# "machine" only as a separate word ("Elastic Machine") or the literal elasticsearchmachine.
BOT_NAME_RE = re.compile(r"\bbot\b|[-_ .]bot\b|(build|push)bot\b|^copilot\b|\bmachine$|^elasticsearchmachine$", re.I)
# Emails that many distinct people share (SVN imports, misconfigured git). Keying on
# them would merge unrelated authors, so such identities key on name instead.
PLACEHOLDER_EMAIL_RE = re.compile(r"^$|^[^@]*$|@[^.]*$|\(none\)|localhost|^no@email$|^unknown(@|$)", re.I)
COAUTHOR_RE = re.compile(r"^Co-authored-by:\s*(.+?)\s*<([^>]+)>\s*$", re.I | re.M)

_REC = "\x1e"  # record separator between commits
_UNIT = "\x1f"  # field separator within the header


@dataclass(frozen=True)
class Identity:
    name: str
    email: str

    @property
    def key(self) -> str:
        if PLACEHOLDER_EMAIL_RE.search(self.email):
            return "name:" + self.name.lower()
        return self.email.lower()

    @property
    def is_bot(self) -> bool:
        return bool(BOT_RE.search(self.name) or BOT_RE.search(self.email) or BOT_NAME_RE.search(self.name))


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
    breadth: int | None = None  # files touched by the commit; None when unknown (per-file --follow mining)
    is_root: bool = False  # no parents

    @property
    def is_bot(self) -> bool:
        return self.author.is_bot

    @property
    def is_noop(self) -> bool:
        """No content change (pure rename, mode change). Carries no knowledge."""
        return self.added == 0 and self.deleted == 0 and not self.binary


@dataclass(frozen=True)
class Touch:
    """One knowledge-bearing commit as seen by one author (primary author or co-author)."""

    date: datetime
    lines: int  # added + deleted in this file
    breadth: int | None  # files touched by the commit; None if unknown
    primary: bool  # False for Co-authored-by credit
    binary: bool
    is_root: bool


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
    touches: list[Touch] = field(default_factory=list)  # newest first; raw input to every scoring shape

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
    resolved = {}
    for i0 in range(0, len(ordered), 500):  # keep argv well under ARG_MAX
        chunk = ordered[i0:i0 + 500]
        out = _git(repo, "check-mailmap", *[f"{i.name} <{i.email}>" for i in chunk])
        for ident, line in zip(chunk, out.splitlines()):
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
                is_root=parents.strip() == "",
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


def _numstat_paths(p: str) -> tuple[str | None, str]:
    """(old, new) for a numstat path; old is None when the line is not a rename.

    Rename forms: "old => new" or "dir/{old => new}/file" (either side may be empty).
    """
    m = re.match(r"^(.*)\{(.*) => (.*)\}(.*)$", p)
    if m:
        old = re.sub(r"/{2,}", "/", f"{m.group(1)}{m.group(2)}{m.group(4)}")
        new = re.sub(r"/{2,}", "/", f"{m.group(1)}{m.group(3)}{m.group(4)}")
        return old, new
    if " => " in p:
        old, new = p.split(" => ", 1)
        return old, new
    return None, p


def _numstat_path(p: str) -> str:
    return _numstat_paths(p)[1]


def mine_file(repo: str | Path, path: str) -> FileHistory:
    """Mine the full --follow history of `path` (relative to repo root) with one git log call."""
    repo = Path(repo)
    all_commits = _parse_log(repo, path)
    return _history_from_commits(path, [c for c in all_commits if not c.is_merge])


def _history_from_commits(path: str, commits: list[Commit]) -> FileHistory:
    """Aggregate per-author facts from a file's non-merge commits (newest first)."""
    content = [c for c in commits if not c.is_noop]  # bots included: their human co-authors earn credit
    human = [c for c in content if not c.is_bot]
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

    for c in content:
        participants = ([] if c.is_bot else [(c.author, True)]) + [
            (co, False) for co in c.coauthors if not co.is_bot and co.key != c.author.key
        ]
        for ident, primary in participants:
            f = get(ident)
            if primary:
                f.commits += 1
                f.lines_changed += c.added + c.deleted
            else:
                f.coauthored_count += 1
            f.first_touch = min(f.first_touch, c.date)
            f.last_touch = max(f.last_touch, c.date)
            f.touches.append(Touch(date=c.date, lines=c.added + c.deleted, breadth=c.breadth,
                                   primary=primary, binary=c.binary, is_root=c.is_root))
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


# --- single walk over the whole history -------------------------------------------------

@dataclass
class CommitMeta:
    sha: str
    author: Identity
    date: datetime
    coauthors: list[Identity]
    is_merge: bool
    breadth: int = 0  # number of (path) records in this commit
    parents: int = 1


@dataclass(frozen=True)
class FileRec:
    pos: int  # index into RepoWalk.commits; 0 is newest
    added: int
    deleted: int
    binary: bool
    renamed_from: str | None


@dataclass
class RepoWalk:
    """Every (commit, path) record from one `git log --numstat -M` over the repository."""

    head: str
    pathspec: str | None
    commits: list[CommitMeta] = field(default_factory=list)  # newest first
    files: dict[str, list[FileRec]] = field(default_factory=dict)  # path -> records, newest first

    def lineage(self, path: str) -> list[tuple[str, FileRec]]:
        """(path-at-the-time, record) newest first, following renames backwards."""
        out: list[tuple[str, FileRec]] = []
        cur: str | None = path
        after = -1  # only records older than the rename we came through
        seen = set()
        while cur is not None and (cur, after) not in seen:
            seen.add((cur, after))
            nxt = None
            for r in self.files.get(cur, []):
                if r.pos <= after:
                    continue
                out.append((cur, r))
                if r.renamed_from is not None and r.renamed_from != cur:
                    nxt, after = r.renamed_from, r.pos
                    break
            cur = nxt
        return out

    def history(self, path: str) -> FileHistory:
        commits = []
        for p, r in self.lineage(path):
            m = self.commits[r.pos]
            commits.append(Commit(sha=m.sha, author=m.author, date=m.date, coauthors=m.coauthors,
                                  added=r.added, deleted=r.deleted, binary=r.binary,
                                  is_merge=m.is_merge, path=p, breadth=m.breadth, is_root=m.parents == 0))
        return _history_from_commits(path, [c for c in commits if not c.is_merge])


def iter_walk(repo: str | Path, pathspec: str | None = None) -> Iterator[tuple[CommitMeta, list[tuple[str, FileRec]]]]:
    """Stream (commit, [(path, record)]) newest first from one git log process.

    Co-author identities are raw here (not mailmapped); `walk()` resolves them in one batch.
    """
    fmt = _REC + _UNIT.join(["%H", "%aN", "%aE", "%at", "%P", "%B"])
    cmd = ["git", "-C", str(repo), "log", "--numstat", "-M", f"--format={fmt}"]
    if pathspec:
        cmd += ["--", pathspec]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    assert proc.stdout is not None
    buf = b""
    pos = 0
    rec_sep = _REC.encode()
    while True:
        chunk = proc.stdout.read(1 << 20)
        if not chunk:
            break
        buf += chunk
        parts = buf.split(rec_sep)
        buf = parts.pop()  # incomplete tail
        for raw in parts:
            if not raw:
                continue
            yield _parse_walk_record(raw.decode("utf-8", errors="replace"), pos)
            pos += 1
    if buf.strip():
        yield _parse_walk_record(buf.decode("utf-8", errors="replace"), pos)
    proc.wait()
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)


def _parse_walk_record(rec: str, pos: int) -> tuple[CommitMeta, list[tuple[str, FileRec]]]:
    sha, name, email, ts, parents, body_and_stat = rec.split(_UNIT, 5)
    body, stat_lines = _split_body_and_numstat(body_and_stat)
    meta = CommitMeta(
        sha=sha, author=Identity(name, email),
        date=datetime.fromtimestamp(int(ts), tz=timezone.utc),
        coauthors=[Identity(n.strip(), e.strip()) for n, e in COAUTHOR_RE.findall(body)],
        is_merge=len(parents.split()) > 1,
        parents=len(parents.split()),
    )
    recs = []
    for line in stat_lines:
        a, d, p = line.split("\t", 2)
        old, new = _numstat_paths(p)
        recs.append((new, FileRec(pos=pos, added=int(a) if a != "-" else 0, deleted=int(d) if d != "-" else 0,
                                  binary=a == "-", renamed_from=old)))
    meta.breadth = len(recs)
    return meta, recs


def walk(repo: str | Path, pathspec: str | None = None) -> RepoWalk:
    """One git log over the repository (or `pathspec`), aggregated in memory."""
    repo = Path(repo)
    head = _git(repo, "rev-parse", "HEAD").strip()
    w = RepoWalk(head=head, pathspec=pathspec)
    raw_coauthors: set[Identity] = set()
    for meta, recs in iter_walk(repo, pathspec):
        w.commits.append(meta)
        raw_coauthors.update(meta.coauthors)
        for path, r in recs:
            w.files.setdefault(path, []).append(r)
    mm = _check_mailmap(repo, raw_coauthors)
    for m in w.commits:
        m.coauthors = [mm.get(i, i) for i in m.coauthors]
    return w
