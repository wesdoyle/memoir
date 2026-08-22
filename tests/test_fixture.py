"""Sanity checks that the synthetic repo has the history P1 tests depend on."""

import subprocess

from build_fixture import EXPECTED


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout


def test_commit_count(fixture_repo):
    assert git(fixture_repo, "rev-list", "--count", "HEAD").strip() == str(EXPECTED["commit_count_main"])


def test_rename_is_followed(fixture_repo):
    out = git(fixture_repo, "log", "--follow", "--name-only", "--format=", "--", "src/helpers.py")
    assert EXPECTED["helpers_old_path"] in out


def test_bot_and_coauthor_and_merge_present(fixture_repo):
    log = git(fixture_repo, "log", "--format=%an|%ae|%P|%B", "--no-mailmap")
    assert EXPECTED["bot"][0] in log
    assert f"Co-authored-by: {EXPECTED['coauthor_of_c04'][0]}" in log
    assert any(len(line.split("|")[2].split()) == 2 for line in log.splitlines() if line.count("|") >= 2)


def test_mailmap_resolves_alias(fixture_repo):
    alias = EXPECTED["mailmap_alias_of_bob"][0]
    raw = git(fixture_repo, "log", "--follow", "--format=%an", "--no-mailmap", "--", "src/helpers.py")
    mapped = git(fixture_repo, "log", "--follow", "--format=%aN", "--", "src/helpers.py")
    assert alias in raw
    assert alias not in mapped


def test_last_committer_of_core_is_lint_sweeper(fixture_repo):
    assert git(fixture_repo, "log", "-1", "--format=%aN", "--", "src/core.py").strip() == EXPECTED["core_last_committer"][0]
