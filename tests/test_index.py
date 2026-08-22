"""On-disk index: built from one walk, queried later; must reproduce live mining."""

import subprocess

from memoir.index import build_index, default_index_path, open_index
from memoir.mining import mine_file


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
            assert b.authors == a.authors, path
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
