"""CLI surface against the fixture repo."""

import json

from typer.testing import CliRunner

from memoir.cli import app

runner = CliRunner()


def run(*args):
    r = runner.invoke(app, list(args), catch_exceptions=False)
    assert r.exit_code == 0, r.output
    return r.output


def test_who_lists_ranked_experts_with_evidence(fixture_repo):
    out = run("who", "src/core.py", "--repo", str(fixture_repo), "--now", "2026-08-21")
    lines = [l for l in out.splitlines() if l.strip().startswith(("1.", "2.", "3."))]
    assert lines[0].split()[1:3] == ["Alice", "Adams"]
    assert "created" in lines[0] and "5 commits" in lines[0]
    assert "Carol Chen" in out and "last commit" in out


def test_who_n_limits_results(fixture_repo):
    out = run("who", "src/core.py", "-n", "1", "--repo", str(fixture_repo))
    assert "Alice Adams" in out and "Carol Chen" not in out.split("last commit")[0]


def test_who_json(fixture_repo):
    data = json.loads(run("who", "src/core.py", "--repo", str(fixture_repo), "--json", "--now", "2026-08-21"))
    assert data["path"] == "src/core.py"
    assert data["experts"][0]["author"]["name"] == "Alice Adams"
    assert {"score", "first_authored", "commits", "lines_changed", "active_span", "last_touch", "coauthored_count"} <= set(data["experts"][0])
    assert data["last_commit"]["author"]["name"] == "Carol Chen"


def test_audit_headline_stat_and_bot_exclusion(fixture_repo):
    out = run("audit", "--repo", str(fixture_repo), "--now", "2026-08-21")
    assert "0/4" in out  # all authors fit in top-3 on this tiny fixture
    assert "1 file" in out and "bot" in out  # requirements.txt excluded


def test_audit_top1_reports_divergence_and_worst_cases(fixture_repo):
    out = run("audit", "--repo", str(fixture_repo), "--top", "1", "--now", "2026-08-21")
    assert "2/4" in out and "50" in out  # README.md: Alice's root-commit creation is not credited, Carol's sweep wins
    assert "src/core.py" in out and "Carol Chen" in out and "Alice Adams" in out
    assert ".mailmap" not in out.split("worst")[1]


def test_audit_subdir(fixture_repo):
    out = run("audit", "src", "--repo", str(fixture_repo), "--top", "1")
    assert "2/2" in out


def test_audit_works_without_a_working_tree(fixture_repo, tmp_path):
    import subprocess
    bare = tmp_path / "nocheckout"
    subprocess.run(["git", "clone", "-q", "--no-checkout", str(fixture_repo), str(bare)], check=True)
    out = run("audit", "--repo", str(bare), "--top", "1", "--now", "2026-08-21")
    assert "2/4" in out


def test_audit_reports_divergence_among_contested_files(fixture_repo):
    # core.py (3 authors), helpers.py (3), README (2), .mailmap (1): none has >1 author... except all but .mailmap
    out = run("audit", "--repo", str(fixture_repo), "--top", "1", "--now", "2026-08-21")
    assert "contested" in out and "2/3" in out  # files with >1 author: core, helpers, README; core and helpers diverge at top-1


def test_who_shows_raw_alongside_decayed(fixture_repo):
    out = run("who", "src/core.py", "--repo", str(fixture_repo), "--now", "2026-08-21")
    first = [l for l in out.splitlines() if l.strip().startswith("1.")][0]
    assert "score 0.97" in first and "raw 3.21" in first  # root-commit creation earns no w_first (not_root)


def test_who_lists_raw_top_when_it_differs(fixture_repo):
    # helpers.py: decayed top-1 is Bob; with -n 1 the raw top-1 is also Bob -> no extra line.
    out = run("who", "src/helpers.py", "--repo", str(fixture_repo), "-n", "1", "--now", "2026-08-21")
    assert "by raw score" not in out
    # core.py with -n 1 far in the future: Carol's recent sweep decays slower than Alice... use a
    # hand-built case instead: 'now' far enough that ordering flips is not available in the fixture,
    # so assert the JSON carries raw_score and raw_rank for agents/humans to compare.
    data = json.loads(run("who", "src/core.py", "--repo", str(fixture_repo), "--json", "--now", "2026-08-21"))
    assert data["experts"][0]["raw_score"] > data["experts"][0]["score"]
    assert [e["author"]["name"] for e in data["by_raw_score"][:2]] == ["Alice Adams", "Carol Chen"]


def test_index_command_then_who_and_audit_use_it(fixture_repo, monkeypatch):
    live = run("who", "src/core.py", "--repo", str(fixture_repo), "--now", "2026-08-21")
    out = run("index", "--repo", str(fixture_repo))
    assert "indexed" in out and "commits" in out
    idx = run("who", "src/core.py", "--repo", str(fixture_repo), "--now", "2026-08-21")
    assert idx == live  # stdout identical; provenance goes to stderr
    audit_idx = run("audit", "--repo", str(fixture_repo), "--top", "1", "--now", "2026-08-21")
    assert "2/4" in audit_idx


def test_stale_index_is_rebuilt_automatically(fixture_repo, tmp_path):
    import subprocess
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(fixture_repo), str(clone)], check=True)
    run("index", "--repo", str(clone))
    env = {"GIT_AUTHOR_NAME": "Zed", "GIT_AUTHOR_EMAIL": "z@example.com", "GIT_COMMITTER_NAME": "Zed",
           "GIT_COMMITTER_EMAIL": "z@example.com", "HOME": str(tmp_path), "GIT_CONFIG_GLOBAL": "/dev/null"}
    (clone / "src" / "core.py").write_text("# rewritten\n")
    subprocess.run(["git", "-C", str(clone), "commit", "-qam", "rewrite"], check=True, env={**env, "PATH": "/usr/bin:/bin"})
    r = runner.invoke(app, ["who", "src/core.py", "--repo", str(clone), "--now", "2026-08-21"], catch_exceptions=False)
    assert r.exit_code == 0
    assert "Zed" in r.output  # the rebuilt index includes the new commit
    assert "index" in r.output and "stale" in r.output  # the rebuild is announced
    r2 = runner.invoke(app, ["who", "src/core.py", "--repo", str(clone), "--now", "2026-08-21"], catch_exceptions=False)
    assert "stale" not in r2.output  # second run: index is fresh, no notice


def test_missing_index_is_built_automatically(fixture_repo, tmp_path):
    import subprocess
    clone = tmp_path / "clone2"
    subprocess.run(["git", "clone", "-q", str(fixture_repo), str(clone)], check=True)
    r = runner.invoke(app, ["who", "src/core.py", "--repo", str(clone), "--json", "--now", "2026-08-21"], catch_exceptions=False)
    assert r.exit_code == 0
    assert "building index" in r.output
    data = json.loads(r.output[r.output.index("{"):])
    assert data["source"] == "index" and data["index_head"]
    assert (clone / ".git" / "memoir" / "index.sqlite").exists()


def test_no_live_flag():
    assert runner.invoke(app, ["who", "x", "--" + "live"]).exit_code == 2


def test_dormant_file_is_announced_and_ranked_by_raw(fixture_repo):
    # all fixture touches are in 2023-2024; with now=2030 everything is >36 months idle
    out = run("who", "src/core.py", "--repo", str(fixture_repo), "--now", "2030-08-21")
    assert "dormant" in out and "raw" in out
    first = [l for l in out.splitlines() if l.strip().startswith("1.")][0]
    assert "Alice Adams" in first
    data = json.loads(run("who", "src/core.py", "--repo", str(fixture_repo), "--now", "2030-08-21", "--json"))
    assert data["dormant"] is True and data["dormant_months"] > 36
    assert data["experts"][0]["author"]["name"] == "Alice Adams"


def test_active_file_is_not_dormant(fixture_repo):
    data = json.loads(run("who", "src/core.py", "--repo", str(fixture_repo), "--now", "2024-06-01", "--json"))
    assert data["dormant"] is False


def test_json_carries_labeled_lists_and_flags(fixture_repo):
    data = json.loads(run("who", "src/core.py", "--repo", str(fixture_repo), "--json", "--now", "2026-08-21"))
    lists = data["lists"]
    assert [e["author"]["name"] for e in lists["current"]][:2] == ["Alice Adams", "Carol Chen"]
    assert [e["author"]["name"] for e in lists["built_it"]][:1] == ["Alice Adams"]
    assert [r["name"] for r in lists["recent"][:2]] == ["Carol Chen", "Alice Adams"]  # last distinct humans, newest first
    assert lists["recent"][0]["email"] == "carol@example.com"
    assert data["flags"]["dormant"] is False
    assert data["flags"]["last_touch_is_sweep"] is False  # Carol's sweep touched 3 files
    assert data["flags"]["last_touch_breadth"] == 3
    assert data["flags"]["stability"]["top1_stable"] in (True, False)
    assert set(data["flags"]["stability"]["top1_by_half_life"]) == {"12", "18", "36", "inf"}
