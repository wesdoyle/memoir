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
    assert "3/4" in out and "75" in out
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
    assert "3/4" in out
