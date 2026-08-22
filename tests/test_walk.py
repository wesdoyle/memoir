"""Single-walk mining must reproduce the per-file --follow miner on every fixture file."""

import subprocess

from memoir.mining import mine_file, walk


def tracked(repo):
    return subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", "--name-only", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.split()


def test_walk_matches_per_file_mining_on_every_fixture_file(fixture_repo):
    w = walk(fixture_repo)
    for path in tracked(fixture_repo):
        a, b = mine_file(fixture_repo, path), w.history(path)
        assert b.paths == a.paths, path
        assert [c.sha for c in b.commits] == [c.sha for c in a.commits], path
        assert b.authors == a.authors, path
        assert b.last_commit.sha == a.last_commit.sha, path


def test_walk_follows_renames_without_follow(fixture_repo):
    h = walk(fixture_repo).history("src/helpers.py")
    assert h.paths == ["src/helpers.py", "src/util.py"]
    assert {a.name for a in h.authors} == {"Bob Smith", "Carol Chen", "Dave Diaz"}


def test_walk_can_be_scoped_to_a_pathspec(fixture_repo):
    w = walk(fixture_repo, pathspec="src")
    assert w.history("src/core.py").authors
    assert w.history("README.md").commits == []  # outside the pathspec: no records


def test_walk_records_head(fixture_repo):
    head = subprocess.run(["git", "-C", str(fixture_repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    assert walk(fixture_repo).head == head
