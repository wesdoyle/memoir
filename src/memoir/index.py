"""On-disk index: the single-walk output persisted in SQLite and queried per file.

Layout (schema v3):
  meta(key, value)                      head sha, pathspec, schema, built_at
  commits(pos, sha, name, email, ts, merge, coauthors, breadth, parents)   pos: smaller = newer (negative after updates)
  files(path, pos, added, deleted, binary, renamed_from)

Facts and scores are derived at query time from these rows (same code path as live
mining), so weights and `now` stay tunable without rebuilding. Stdlib sqlite3 only.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from memoir.mining import (
    Commit,
    FileHistory,
    Identity,
    _check_mailmap,
    _history_from_commits,
    iter_walk,
)

SCHEMA = 3
NEWEST = -(1 << 62)  # "older than nothing": pos is an ordering key (smaller = newer) and may be negative


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def default_index_path(repo: str | Path) -> Path:
    """<git-dir>/memoir/index.sqlite — inside .git, never in the worktree or a diff."""
    git_dir = Path(_git(Path(repo), "rev-parse", "--absolute-git-dir").strip())
    return git_dir / "memoir" / "index.sqlite"


def _ingest(con: sqlite3.Connection, repo: Path, pathspec: str | None, revisions: str, first_pos: int) -> int:
    """Stream a walk into the open connection. Positions run first_pos, first_pos+1, ... in log order
    (newest first); `pos` is an ordering key only — smaller is newer. Returns the number of commits."""
    raw_coauthors: set[Identity] = set()
    crows, frows = [], []
    pending: list[tuple[int, list[Identity]]] = []
    for meta, recs in iter_walk(repo, pathspec, revisions):
        pos = first_pos + len(crows)
        crows.append((pos, meta.sha, meta.author.name, meta.author.email,
                      int(meta.date.timestamp()), int(meta.is_merge), None, meta.breadth, meta.parents))
        if meta.coauthors:
            pending.append((pos, meta.coauthors))
            raw_coauthors.update(meta.coauthors)
        for path, r in recs:
            frows.append((path, pos, r.added, r.deleted, int(r.binary), r.renamed_from))
        if len(frows) >= 50_000:
            con.executemany("INSERT INTO files VALUES (?,?,?,?,?,?)", frows)
            frows = []
    con.executemany("INSERT INTO files VALUES (?,?,?,?,?,?)", frows)
    con.executemany("INSERT INTO commits VALUES (?,?,?,?,?,?,?,?,?)", crows)
    mm = _check_mailmap(repo, raw_coauthors)
    con.executemany(
        "UPDATE commits SET coauthors=? WHERE pos=?",
        [(json.dumps([[mm.get(i, i).name, mm.get(i, i).email] for i in cos]), pos) for pos, cos in pending],
    )
    return len(crows)


def build_index(repo: str | Path, db_path: str | Path, pathspec: str | None = None) -> Path:
    """Walk the repository once and (re)write the index at db_path. Returns db_path."""
    repo, db_path = Path(repo), Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = db_path.with_suffix(".tmp")
    if tmp.exists():
        tmp.unlink()
    head = _git(repo, "rev-parse", "HEAD").strip()
    con = sqlite3.connect(tmp)
    try:
        con.executescript(
            """
            PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
            CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE commits(pos INTEGER PRIMARY KEY, sha TEXT, name TEXT, email TEXT,
                                 ts INTEGER, merge INTEGER, coauthors TEXT, breadth INTEGER, parents INTEGER);
            CREATE TABLE files(path TEXT, pos INTEGER, added INTEGER, deleted INTEGER,
                               binary INTEGER, renamed_from TEXT);
            """
        )
        n = _ingest(con, repo, pathspec, "HEAD", 0)
        con.execute("CREATE INDEX files_path ON files(path, pos)")
        con.execute("CREATE INDEX commits_sha ON commits(sha)")
        con.executemany(
            "INSERT INTO meta VALUES (?,?)",
            [("head", head), ("pathspec", pathspec or ""), ("schema", str(SCHEMA)),
             ("built_at", datetime.now(tz=timezone.utc).isoformat(timespec="seconds")),
             ("commits", str(n))],
        )
        con.commit()
    finally:
        con.close()
    tmp.replace(db_path)
    return db_path


def update_index(repo: str | Path, db_path: str | Path) -> str:
    """Bring the index at db_path up to HEAD. Returns "fresh" (nothing to do), "incremental"
    (only old_head..HEAD was walked and prepended with positions below the current minimum), or
    "rebuilt" (no usable index, schema changed, or HEAD is not a descendant of the indexed head —
    e.g. after a rebase/amend — so the whole history was walked again)."""
    repo, db_path = Path(repo), Path(db_path)
    head = _git(repo, "rev-parse", "HEAD").strip()
    if not db_path.exists():
        build_index(repo, db_path)
        return "rebuilt"
    con = sqlite3.connect(db_path)
    try:
        meta = dict(con.execute("SELECT key, value FROM meta"))
        old = meta.get("head")
        if meta.get("schema") != str(SCHEMA) or not old:
            con.close()
            build_index(repo, db_path, meta.get("pathspec") or None)
            return "rebuilt"
        if old == head:
            return "fresh"
        ok = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", old, head]).returncode == 0
        if not ok:
            con.close()
            build_index(repo, db_path, meta.get("pathspec") or None)
            return "rebuilt"
        (min_pos,) = con.execute("SELECT MIN(pos) FROM commits").fetchone()
        n_new = int(_git(repo, "rev-list", "--count", f"{old}..{head}"))
        con.execute("PRAGMA journal_mode=OFF")
        con.execute("PRAGMA synchronous=OFF")
        n = _ingest(con, repo, meta.get("pathspec") or None, f"{old}..{head}", (min_pos or 0) - n_new)
        con.execute("UPDATE meta SET value=? WHERE key='head'", (head,))
        con.execute("UPDATE meta SET value=? WHERE key='commits'", (str(int(meta.get("commits", "0")) + n),))
        con.execute("INSERT OR REPLACE INTO meta VALUES ('updated_at', ?)",
                    (datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),))
        con.commit()
        return "incremental"
    finally:
        con.close()


class Index:
    def __init__(self, con: sqlite3.Connection):
        self.con = con
        self.meta = dict(con.execute("SELECT key, value FROM meta"))

    # -- lifecycle
    def close(self) -> None:
        self.con.close()

    def __enter__(self) -> Index:
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    # -- metadata
    @property
    def head(self) -> str:
        return self.meta["head"]

    @property
    def pathspec(self) -> str | None:
        return self.meta.get("pathspec") or None

    def is_fresh(self, repo: str | Path) -> bool:
        return self.meta.get("schema") == str(SCHEMA) and _git(Path(repo), "rev-parse", "HEAD").strip() == self.head

    def covers(self, path: str) -> bool:
        ps = self.pathspec
        return ps is None or path == ps or path.startswith(ps.rstrip("/") + "/")

    # -- queries
    def pos_of(self, sha: str) -> int | None:
        """Ordering key of a commit: smaller is newer; not contiguous after incremental updates."""
        row = self.con.execute("SELECT pos FROM commits WHERE sha=?", (sha,)).fetchone()
        return row[0] if row else None

    def _records(self, path: str, after: int) -> list[tuple[int, int, int, int, str | None]]:
        return self.con.execute(
            "SELECT pos, added, deleted, binary, renamed_from FROM files WHERE path=? AND pos>? ORDER BY pos",
            (path, after),
        ).fetchall()

    def lineage(self, path: str, before: int | None = None) -> list[tuple[str, int, int, int, bool, str | None]]:
        """Records newest first following renames backwards; `before` = only commits older than that pos
        (pos 0 is HEAD), i.e. the file's history as it was just before commit `before`."""
        out = []
        cur: str | None = path
        after = NEWEST if before is None else before
        seen = set()
        while cur is not None and (cur, after) not in seen:
            seen.add((cur, after))
            nxt = None
            for pos, added, deleted, binary, renamed_from in self._records(cur, after):
                out.append((cur, pos, added, deleted, bool(binary), renamed_from))
                if renamed_from is not None and renamed_from != cur:
                    nxt, after = renamed_from, pos
                    break
            cur = nxt
        return out

    def history(self, path: str, before: int | None = None) -> FileHistory:
        lin = self.lineage(path, before)
        if not lin:
            return _history_from_commits(path, [])
        positions = [l[1] for l in lin]
        rows = self.con.execute(
            f"SELECT pos, sha, name, email, ts, merge, coauthors, breadth, parents FROM commits WHERE pos IN ({','.join('?' * len(positions))})",
            positions,
        ).fetchall()
        by_pos = {r[0]: r for r in rows}
        commits = []
        for p, pos, added, deleted, binary, _ in lin:
            _, sha, name, email, ts, merge, coauthors, breadth, parents = by_pos[pos]
            commits.append(Commit(
                sha=sha, author=Identity(name, email),
                date=datetime.fromtimestamp(ts, tz=timezone.utc),
                coauthors=[Identity(n, e) for n, e in json.loads(coauthors)] if coauthors else [],
                added=added, deleted=deleted, binary=binary, is_merge=bool(merge), path=p, breadth=breadth,
                is_root=parents == 0,
            ))
        return _history_from_commits(path, [c for c in commits if not c.is_merge])


def open_index(db_path: str | Path) -> Index:
    con = sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True)
    return Index(con)
