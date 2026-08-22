"""On-disk index: the single-walk output persisted in SQLite and queried per file.

Layout (schema v4):
  meta(key, value)          head, pathspec, schema, built_at, rank_now, rank_weights
  commits(pos, sha, name, email, ts, merge, coauthors, breadth, parents)   pos: smaller = newer (negative after updates)
  files(path, pos, added, deleted, binary, renamed_from)                  raw (commit, path) records
  file_lineage(path, pos)   for every file at HEAD: the commits in its history (renames followed)
  file_rank(path, key, name, email, rank_cur, score, rank_raw, raw)      top-5 of each list per HEAD file,
                            computed at rank_now with rank_weights; `person`/`audit` read these

Facts and scores are derived at query time from these rows (same code path as live
mining), so weights and `now` stay tunable without rebuilding. Stdlib sqlite3 only.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from memoir.mining import (
    Commit,
    FileHistory,
    Identity,
    _check_mailmap,
    _history_from_commits,
    iter_walk,
)
from memoir.scoring import Weights, rank

SCHEMA = 4
RANK_TOP = 5
RANK_STALE_DAYS = 30  # decay moves slowly (HL 18 months); recompute all ranks when rank_now is older than this
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


def _head_files(repo: Path, pathspec: str | None) -> list[str]:
    args = ["ls-tree", "-r", "--name-only", "-z", "HEAD"] + (["--", pathspec] if pathspec else [])
    return [f for f in _git(repo, *args).split("\0") if f]


def _materialize(con: sqlite3.Connection, repo: Path, paths: list[str], now: datetime, w: Weights,
                 lineage: bool = True, ranks: bool = True) -> None:
    """(Re)compute file_lineage and/or file_rank rows for the given HEAD paths."""
    ix = Index(con)
    if lineage:
        con.executemany("DELETE FROM file_lineage WHERE path=?", [(p,) for p in paths])
    if ranks:
        con.executemany("DELETE FROM file_rank WHERE path=?", [(p,) for p in paths])
    lrows, rrows = [], []
    for p in paths:
        lin = ix.lineage(p)
        if lineage:
            lrows += [(p, pos) for _, pos, *_ in lin]
        if ranks:
            h = ix.history(p) if lin else None
            if h and h.authors:
                r = rank(h, now=now, w=w)
                by_raw = sorted(r, key=lambda e: (-e.raw_score, e.author.name, e.author.email))
                cur = {e.author.key: (i, e) for i, e in enumerate(r[:RANK_TOP], 1)}
                rawr = {e.author.key: (i, e) for i, e in enumerate(by_raw[:RANK_TOP], 1)}
                for key in cur.keys() | rawr.keys():
                    e = (cur.get(key) or rawr.get(key))[1]
                    rrows.append((p, key, e.author.name, e.author.email,
                                  cur[key][0] if key in cur else None, e.score,
                                  rawr[key][0] if key in rawr else None, e.raw_score))
        if len(lrows) > 50_000:
            con.executemany("INSERT INTO file_lineage VALUES (?,?)", lrows); lrows = []
    con.executemany("INSERT INTO file_lineage VALUES (?,?)", lrows)
    con.executemany("INSERT INTO file_rank VALUES (?,?,?,?,?,?,?,?)", rrows)


def build_index(repo: str | Path, db_path: str | Path, pathspec: str | None = None,
                now: datetime | None = None, w: Weights = Weights()) -> Path:
    """Walk the repository once and (re)write the index at db_path. Returns db_path."""
    repo, db_path = Path(repo), Path(db_path)
    now = now or datetime.now(tz=timezone.utc)
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
            CREATE TABLE file_lineage(path TEXT, pos INTEGER);
            CREATE TABLE file_rank(path TEXT, key TEXT, name TEXT, email TEXT, rank_cur INTEGER,
                                   score REAL, rank_raw INTEGER, raw REAL);
            """
        )
        n = _ingest(con, repo, pathspec, "HEAD", 0)
        con.execute("CREATE INDEX files_path ON files(path, pos)")
        con.execute("CREATE INDEX commits_sha ON commits(sha)")
        con.executemany(
            "INSERT INTO meta VALUES (?,?)",
            [("head", head), ("pathspec", pathspec or ""), ("schema", str(SCHEMA)),
             ("built_at", datetime.now(tz=timezone.utc).isoformat(timespec="seconds")),
             ("commits", str(n)),
             ("rank_now", now.isoformat(timespec="seconds")), ("rank_weights", json.dumps(asdict(w)))],
        )
        _materialize(con, repo, _head_files(repo, pathspec), now, w)
        con.execute("CREATE INDEX file_lineage_path ON file_lineage(path)")
        con.execute("CREATE INDEX file_lineage_pos ON file_lineage(pos)")
        con.execute("CREATE INDEX file_rank_path ON file_rank(path)")
        con.execute("CREATE INDEX file_rank_key ON file_rank(key)")
        con.commit()
    finally:
        con.close()
    tmp.replace(db_path)
    return db_path


def update_index(repo: str | Path, db_path: str | Path, now: datetime | None = None) -> str:
    """Bring the index at db_path up to HEAD (and its materialized ranks up to `now`). Returns
    "fresh" (nothing to do), "reranked" (HEAD unchanged but rank_now was stale: all ranks recomputed),
    "incremental" (only old_head..HEAD was walked and prepended with positions below the current
    minimum; lineage and ranks recomputed for the touched paths, all ranks if rank_now was stale), or
    "rebuilt" (no usable index, schema changed, or HEAD is not a descendant of the indexed head —
    e.g. after a rebase/amend — so the whole history was walked again)."""
    repo, db_path = Path(repo), Path(db_path)
    now = now or datetime.now(tz=timezone.utc)
    head = _git(repo, "rev-parse", "HEAD").strip()
    if not db_path.exists():
        build_index(repo, db_path, now=now)
        return "rebuilt"
    con = sqlite3.connect(db_path)
    try:
        meta = dict(con.execute("SELECT key, value FROM meta"))
        old = meta.get("head")
        pathspec = meta.get("pathspec") or None
        if meta.get("schema") != str(SCHEMA) or not old:
            con.close()
            build_index(repo, db_path, pathspec, now=now)
            return "rebuilt"
        w = Weights(**json.loads(meta["rank_weights"]))
        stale = not Index(con).ranks_fresh(now)
        if old == head and not stale:
            return "fresh"
        con.execute("PRAGMA journal_mode=OFF")
        con.execute("PRAGMA synchronous=OFF")
        if old == head:
            _materialize(con, repo, _head_files(repo, pathspec), now, w, lineage=False, ranks=True)
            con.execute("UPDATE meta SET value=? WHERE key='rank_now'", (now.isoformat(timespec="seconds"),))
            con.commit()
            return "reranked"
        ok = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", old, head]).returncode == 0
        if not ok:
            con.close()
            build_index(repo, db_path, pathspec, now=now)
            return "rebuilt"
        (min_pos,) = con.execute("SELECT MIN(pos) FROM commits").fetchone()
        n_new = int(_git(repo, "rev-list", "--count", f"{old}..{head}"))
        first = (min_pos or 0) - n_new
        n = _ingest(con, repo, pathspec, f"{old}..{head}", first)
        # maintain materialization: paths at HEAD only; touched paths get new lineage + ranks
        head_files = _head_files(repo, pathspec)
        head_set = set(head_files)
        touched = {p for (p,) in con.execute("SELECT DISTINCT path FROM files WHERE pos < ?", (first + n,))}
        gone = [p for (p,) in con.execute("SELECT DISTINCT path FROM file_lineage") if p not in head_set]
        con.executemany("DELETE FROM file_lineage WHERE path=?", [(p,) for p in gone])
        con.executemany("DELETE FROM file_rank WHERE path=?", [(p,) for p in gone])
        known = {p for (p,) in con.execute("SELECT DISTINCT path FROM file_lineage")}
        redo = sorted((touched & head_set) | (head_set - known))  # touched, plus brand-new or renamed-to paths
        _materialize(con, repo, redo, now, w)
        if stale:
            _materialize(con, repo, head_files, now, w, lineage=False, ranks=True)
            con.execute("UPDATE meta SET value=? WHERE key='rank_now'", (now.isoformat(timespec="seconds"),))
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

    @property
    def rank_now(self) -> datetime:
        return datetime.fromisoformat(self.meta["rank_now"])

    @property
    def rank_weights(self) -> Weights:
        return Weights(**json.loads(self.meta["rank_weights"]))

    def ranks_fresh(self, now: datetime, days: int = RANK_STALE_DAYS) -> bool:
        return abs(now - self.rank_now) <= timedelta(days=days)

    # -- materialized queries
    def ranks_for(self, path: str) -> list[tuple]:
        """[(key, name, email, rank_cur|None, score, rank_raw|None, raw)] for a HEAD path."""
        return self.con.execute(
            "SELECT key, name, email, rank_cur, score, rank_raw, raw FROM file_rank WHERE path=?", (path,)).fetchall()

    def files_touched_by(self, keys: set[str]) -> list[str]:
        """HEAD paths whose lineage contains a commit by any of these identity keys (author or co-author)."""
        emails = [k for k in keys if not k.startswith("name:")]
        names = [k[5:] for k in keys if k.startswith("name:")]
        cond, args = [], []
        if emails:
            cond.append(f"LOWER(c.email) IN ({','.join('?' * len(emails))})"); args += emails
        if names:
            cond.append(f"LOWER(c.name) IN ({','.join('?' * len(names))})"); args += names
        for e in emails:
            cond.append("c.coauthors LIKE ?"); args.append(f"%{e}%")
        if not cond:
            return []
        rows = self.con.execute(
            f"SELECT DISTINCT l.path FROM file_lineage l JOIN commits c ON c.pos=l.pos WHERE {' OR '.join(cond)}", args)
        return sorted(p for (p,) in rows)

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
