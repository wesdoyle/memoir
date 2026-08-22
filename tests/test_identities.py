"""memoir identities: suggest .mailmap lines for split identities (nothing is written)."""

import subprocess
from pathlib import Path

from memoir.identities import suggest_mailmap
from memoir.index import build_index, open_index


def _repo(tmp_path: Path) -> Path:
    r = tmp_path / "split"
    r.mkdir()
    def git(*a, name, email, date):
        env = {"GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email, "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
               "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date, "GIT_CONFIG_GLOBAL": "/dev/null", "HOME": str(r), "PATH": "/usr/bin:/bin"}
        subprocess.run(["git", "-C", str(r), *a], check=True, capture_output=True, env=env)
    git("init", "-q", "-b", "main", name="x", email="x@x", date="2024-01-01T00:00:00")
    authors = [("Zed Zee", "zed@work.example", 3), ("Zed Zee", "zed@home.example", 2),
               ("Zed Zee", "1234+zedz@users.noreply.github.com", 1), ("zedz", "zedz@other.example", 1),
               ("Ann Lee", "ann@x.example", 2), ("ann", "ann@x.example", 1), ("Bo", "bo@a.example", 1), ("Bo", "bo@b.example", 1)]
    i = 0
    for name, email, n in authors:
        for _ in range(n):
            (r / f"f{i}.txt").write_text(str(i))
            git("add", "-A", name=name, email=email, date=f"2024-01-{i+1:02d}T00:00:00")
            git("commit", "-qm", f"c{i}", name=name, email=email, date=f"2024-01-{i+1:02d}T00:00:00")
            i += 1
    return r


def test_suggest_mailmap_tiers(tmp_path):
    r = _repo(tmp_path)
    db = tmp_path / "i.sqlite"
    build_index(r, db)
    with open_index(db) as ix:
        out = suggest_mailmap(ix)
    high = {line for line, _ in out["high"]}
    assert "Zed Zee <zed@work.example> Zed Zee <zed@home.example>" in high  # canonical = most commits
    assert "Zed Zee <zed@work.example> Zed Zee <1234+zedz@users.noreply.github.com>" in high
    noreply = {line for line, _ in out["noreply"]}
    assert any("zedz@other.example" in l or "1234+zedz" in l for l in noreply)  # login zedz links the noreply address
    names = {line for line, _ in out["names"]}
    assert "Ann Lee <ann@x.example> ann <ann@x.example>" in names
    # single-token names are never merged by name
    assert not any("Bo <bo@a.example> Bo <bo@b.example>" in l or "Bo <bo@b.example> Bo <bo@a.example>" in l for l in high)


def test_identities_cli_prints_a_mailmap_block(fixture_repo, tmp_path):
    from typer.testing import CliRunner
    from memoir.cli import app
    r = _repo(tmp_path)
    out = CliRunner().invoke(app, ["identities", "--repo", str(r)], catch_exceptions=False)
    assert out.exit_code == 0, out.output
    assert "# high" in out.output and "Zed Zee <zed@work.example> Zed Zee <zed@home.example>" in out.output
    assert "nothing is written" in out.output.lower() or "review" in out.output.lower()
