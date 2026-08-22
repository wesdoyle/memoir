"""On-disk index: the single-walk output persisted in SQLite and queried per file.

Layout (schema v3):
  meta(key, value)                      head sha, pathspec, schema, built_at
  commits(pos, sha, name, email, ts, merge, coauthors, breadth, parents)   pos 0 = newest
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


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def default_index_path(repo: str | Path) -> Path:
    """<git-dir>/memoir/index.sqlite — inside .git, never in the worktree or a diff."""
    git_dir = Path(_git(Path(repo), "rev-parse", "--absolute-git-dir").strip())
    return git_dir / "memoir" / "index.sqlite"


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
        raw_coauthors: set[Identity] = set()
        crows, frows = [], []
        pending: list[tuple[int, list[Identity]]] = []
        for meta, recs in iter_walk(repo, pathspec):
            pos = len(crows)
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
        con.execute("CREATE INDEX files_path ON files(path, pos)")
        con.executemany(
            "INSERT INTO meta VALUES (?,?)",
            [("head", head), ("pathspec", pathspec or ""), ("schema", str(SCHEMA)),
             ("built_at", datetime.now(tz=timezone.utc).isoformat(timespec="seconds")),
             ("commits", str(len(crows)))],
        )
        con.commit()
    finally:
        con.close()
    tmp.replace(db_path)
    return db_path


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
    def _records(self, path: str, after: int) -> list[tuple[int, int, int, int, str | None]]:
        return self.con.execute(
            "SELECT pos, added, deleted, binary, renamed_from FROM files WHERE path=? AND pos>? ORDER BY pos",
            (path, after),
        ).fetchall()

    def lineage(self, path: str) -> list[tuple[str, int, int, int, bool, str | None]]:
        out = []
        cur: str | None = path
        after = -1
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

    def history(self, path: str) -> FileHistory:
        lin = self.lineage(path)
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
