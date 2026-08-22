"""Mining: git history -> per-(file, author) facts. Runs against the synthetic fixture."""

from memoir.mining import mine_file


def by_name(history):
    return {a.name: a for a in history.authors}


def test_merge_commits_are_excluded(fixture_repo):
    h = mine_file(fixture_repo, "src/core.py")
    assert len(h.commits) == 6  # 5 alice + 1 carol; merge touched nothing
    assert all(not c.is_merge for c in h.commits)


def test_rename_history_is_followed(fixture_repo):
    h = mine_file(fixture_repo, "src/helpers.py")
    assert "src/util.py" in h.paths
    bob = by_name(h)["Bob Smith"]
    assert bob.first_authored is True
    assert bob.commits == 2  # create, alias edit (rename is a no-op)


def test_mailmap_merges_alias_identity(fixture_repo):
    h = mine_file(fixture_repo, "src/helpers.py")
    assert "Robert B" not in by_name(h)
    assert by_name(h)["Bob Smith"].email == "bob@example.com"


def test_bot_commits_are_excluded_from_facts_but_visible_as_last_commit(fixture_repo):
    h = mine_file(fixture_repo, "requirements.txt")
    assert "dependabot[bot]" not in by_name(h)
    assert h.last_commit.author.name == "dependabot[bot]"
    assert h.last_commit.is_bot is True


def test_human_coauthor_of_bot_commit_is_credited(fixture_repo):
    dave = by_name(mine_file(fixture_repo, "requirements.txt"))["Dave Diaz"]
    assert dave.commits == 0
    assert dave.coauthored_count == 1


def test_coauthor_is_credited_as_coauthor_not_committer(fixture_repo):
    dave = by_name(mine_file(fixture_repo, "src/core.py"))["Dave Diaz"]
    assert dave.commits == 0
    assert dave.coauthored_count == 1


def test_others_commits_since_last_touch(fixture_repo):
    a = by_name(mine_file(fixture_repo, "src/core.py"))
    assert a["Alice Adams"].others_commits_since == 1  # carol's sweep
    assert a["Carol Chen"].others_commits_since == 0


def test_first_authored_and_lines(fixture_repo):
    a = by_name(mine_file(fixture_repo, "src/core.py"))
    assert a["Alice Adams"].first_authored is True
    assert a["Carol Chen"].first_authored is False
    assert a["Carol Chen"].lines_changed == 30
    assert a["Alice Adams"].lines_changed == 26 + 6 + 6 + 3 + 3


def test_pure_rename_carries_no_knowledge(fixture_repo):
    h = mine_file(fixture_repo, "src/helpers.py")
    bob = by_name(h)["Bob Smith"]
    assert bob.commits == 2  # create + alias edit; the rename commit is not a delivery
    assert bob.last_touch.date().isoformat() == "2023-05-20"
    assert "src/util.py" in h.paths  # path lineage still tracked
    rename = next(c for c in h.commits if c.path == "src/helpers.py" and c.added == 0 and c.deleted == 0)
    assert rename.is_noop is True
