"""On-disk index: built from one walk, queried later; must reproduce live mining."""

import subprocess

from memoir.index import build_index, default_index_path, open_index
from memoir.mining import mine_file


def _norm(authors):
    """Per-file --follow mining cannot know commit breadth; compare facts with it blanked."""
    from dataclasses import replace
    return [replace(a, touches=[replace(t, breadth=None) for t in a.touches]) for a in authors]


def tracked(repo):
    return subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", "--name-only", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.split()


def test_index_reproduces_live_mining(fixture_repo, tmp_path):
    db = tmp_path / "idx.sqlite"
    build_index(fixture_repo, db)
    with open_index(db) as ix:
        for path in tracked(fixture_repo):
            a, b = mine_file(fixture_repo, path), ix.history(path)
            assert [c.sha for c in b.commits] == [c.sha for c in a.commits], path
            assert _norm(b.authors) == _norm(a.authors), path
            assert b.paths == a.paths, path
            assert b.last_commit.sha == a.last_commit.sha


def test_index_default_location_is_inside_git_dir(fixture_repo):
    p = default_index_path(fixture_repo)
    assert p.parent.name == "memoir" and p.parent.parent == fixture_repo / ".git"


def test_index_freshness_tracks_head(fixture_repo, tmp_path):
    db = tmp_path / "idx.sqlite"
    build_index(fixture_repo, db)
    head = subprocess.run(["git", "-C", str(fixture_repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    with open_index(db) as ix:
        assert ix.head == head
        assert ix.is_fresh(fixture_repo)
        assert ix.covers("src/core.py") and ix.covers("README.md")


def test_index_scoped_to_pathspec_reports_coverage(fixture_repo, tmp_path):
    db = tmp_path / "idx.sqlite"
    build_index(fixture_repo, db, pathspec="src")
    with open_index(db) as ix:
        assert ix.covers("src/core.py")
        assert not ix.covers("README.md")


def test_index_is_rebuilt_in_place(fixture_repo, tmp_path):
    db = tmp_path / "idx.sqlite"
    build_index(fixture_repo, db)
    build_index(fixture_repo, db)  # second build must not duplicate rows
    with open_index(db) as ix:
        assert len(ix.history("src/core.py").commits) == 6


def test_index_stores_breadth(fixture_repo, tmp_path):
    db = tmp_path / "idx.sqlite"
    build_index(fixture_repo, db)
    with open_index(db) as ix:
        h = ix.history("src/core.py")
        assert {c.author.name: c.breadth for c in h.commits}["Carol Chen"] == 3


def test_history_before_a_position_excludes_newer_commits(fixture_repo, tmp_path):
    db = tmp_path / "idx.sqlite"
    build_index(fixture_repo, db)
    with open_index(db) as ix:
        full = ix.history("src/core.py")
        # pos 0 is Carol's sweep (newest). History strictly before it must not contain her.
        carol_pos = ix.con.execute("SELECT pos FROM commits WHERE name='Carol Chen'").fetchone()[0]
        before = ix.history("src/core.py", before=carol_pos)
        assert "Carol Chen" not in {a.name for a in before.authors}
        assert len(before.commits) == len(full.commits) - 1
        assert before.last_commit.author.name == "Alice Adams"


def _git(repo, *args, env=None):
    import os
    e = {**os.environ, "GIT_AUTHOR_NAME": "Zed", "GIT_AUTHOR_EMAIL": "z@example.com", "GIT_COMMITTER_NAME": "Zed",
         "GIT_COMMITTER_EMAIL": "z@example.com", "GIT_CONFIG_GLOBAL": "/dev/null", "HOME": str(repo)}
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env={**e, **(env or {})}).stdout


def _same(a, b):
    return ([c.sha for c in a.commits] == [c.sha for c in b.commits] and a.authors == b.authors and a.paths == b.paths
            and (a.last_commit.sha if a.last_commit else None) == (b.last_commit.sha if b.last_commit else None))


def test_incremental_update_matches_full_rebuild(fixture_repo, tmp_path):
    from memoir.index import update_index
    clone = tmp_path / "c"
    subprocess.run(["git", "clone", "-q", str(fixture_repo), str(clone)], check=True)
    tip = _git(clone, "rev-parse", "HEAD").strip()
    _git(clone, "checkout", "-q", "HEAD~6")  # index at an older commit: before the rename, merge, co-author, bot, sweep
    db = tmp_path / "inc.sqlite"
    build_index(clone, db)
    _git(clone, "checkout", "-q", tip)
    how = update_index(clone, db)
    assert how == "incremental"
    full = tmp_path / "full.sqlite"
    build_index(clone, full)
    with open_index(db) as inc, open_index(full) as ref:
        assert inc.head == ref.head == tip
        assert inc.meta["commits"] == ref.meta["commits"]
        assert inc.con.execute("SELECT COUNT(*) FROM files").fetchone() == ref.con.execute("SELECT COUNT(*) FROM files").fetchone()
        assert inc.con.execute("SELECT COUNT(DISTINCT pos) FROM commits").fetchone()[0] == int(inc.meta["commits"])  # no duplicate positions
        for path in tracked(clone):
            assert _same(inc.history(path), ref.history(path)), path
        # newest-first ordering survives across the boundary
        pos = [c for (c,) in inc.con.execute("SELECT pos FROM commits ORDER BY pos")]
        shas = [s for (s,) in inc.con.execute("SELECT sha FROM commits ORDER BY pos")]
        assert shas == _git(clone, "log", "--format=%H").split()


def test_update_is_noop_when_fresh_and_rebuilds_when_head_is_not_a_descendant(fixture_repo, tmp_path):
    from memoir.index import update_index
    clone = tmp_path / "c2"
    subprocess.run(["git", "clone", "-q", str(fixture_repo), str(clone)], check=True)
    db = tmp_path / "inc2.sqlite"
    build_index(clone, db)
    assert update_index(clone, db) == "fresh"
    (clone / "src" / "core.py").write_text("# amended\n")
    _git(clone, "commit", "-qa", "--amend", "--reset-author", "-m", "rewritten history")
    assert update_index(clone, db) == "rebuilt"
    with open_index(db) as ix:
        assert ix.head == _git(clone, "rev-parse", "HEAD").strip()
        assert "Zed" in {a.name for a in ix.history("src/core.py").authors}


def test_update_after_new_commits_credits_them(fixture_repo, tmp_path):
    from memoir.index import update_index
    clone = tmp_path / "c3"
    subprocess.run(["git", "clone", "-q", str(fixture_repo), str(clone)], check=True)
    db = tmp_path / "inc3.sqlite"
    build_index(clone, db)
    (clone / "src" / "core.py").write_text("# new\n")
    _git(clone, "commit", "-qam", "edit by zed")
    assert update_index(clone, db) == "incremental"
    with open_index(db) as ix:
        h = ix.history("src/core.py")
        assert h.last_commit.author.name == "Zed" and len(h.commits) == 7
