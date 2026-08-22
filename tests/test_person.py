"""memoir person: the reverse question — what does this person know — as a rollup."""

import json

from typer.testing import CliRunner

from memoir.cli import app
from memoir.index import default_index_path, open_index
from memoir.person import person_report, resolve_person

runner = CliRunner()


def run(*args):
    r = runner.invoke(app, list(args), catch_exceptions=False)
    assert r.exit_code == 0, r.output
    return r.output


def test_resolve_exact_email_name_and_ambiguity(fixture_repo):
    run("index", "--repo", str(fixture_repo))
    with open_index(default_index_path(fixture_repo)) as ix:
        keys, note = resolve_person(ix, "alice@example.com")
        assert keys == {"alice@example.com"} and note is None
        keys, note = resolve_person(ix, "carol")
        assert keys == {"carol@example.com"}
        keys, note = resolve_person(ix, "example.com")  # matches everyone -> ambiguous
        assert keys == set() and "ambiguous" in note
        keys, note = resolve_person(ix, "nobody")
        assert keys == set() and "no author" in note


def test_person_rollup_names_territory_through_renames(fixture_repo):
    with open_index(default_index_path(fixture_repo)) as ix:
        rep = person_report(ix, {"bob@example.com"}, now="2026-08-21")
    # Bob only ever committed to src/util.py, which is src/helpers.py at HEAD
    paths = [f["path"] for f in rep["top_files"]["current"]] + [f["path"] for f in rep["top_files"]["built_it"]]
    assert "src/helpers.py" in paths and "src/util.py" not in paths
    assert rep["summary"]["files"] == 1 and rep["summary"]["top3_built_it"] == 1


def test_person_rollup_alice_and_carol(fixture_repo):
    with open_index(default_index_path(fixture_repo)) as ix:
        alice = person_report(ix, {"alice@example.com"}, now="2026-08-21")
        carol = person_report(ix, {"carol@example.com"}, now="2026-08-21")
    assert alice["top_files"]["current"][0]["path"] == "src/core.py"
    assert alice["top_files"]["built_it"][0]["path"] == "src/core.py"
    assert alice["summary"]["last_touch"] == "2024-01-15"
    # Carol's sweep touched 3 files but she built nothing: built_it weaker than current
    assert carol["summary"]["top3_built_it"] <= carol["summary"]["top3_current"]
    assert any(d["dir"] == "src" for d in alice["directories"])
    assert isinstance(alice["themes"], list)


def test_person_cli_text_and_json(fixture_repo):
    out = run("person", "Alice", "--repo", str(fixture_repo), "--now", "2026-08-21")
    assert "Alice Adams" in out and "src/core.py" in out and "built_it" in out and "current" in out
    data = json.loads(run("person", "alice@example.com", "--repo", str(fixture_repo), "--now", "2026-08-21", "--json"))
    assert data["person"]["keys"] == ["alice@example.com"]
    assert {"summary", "themes", "top_files", "directories"} <= set(data)
    amb = runner.invoke(app, ["person", "example.com", "--repo", str(fixture_repo)])
    assert amb.exit_code != 0 and "ambiguous" in amb.output


def test_split_identities_take_the_strongest_row_per_file(tmp_path):
    import subprocess
    from memoir.index import build_index
    r = tmp_path / "split2"; r.mkdir()
    def git(*a, name, email, date):
        env = {"GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email, "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
               "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date, "GIT_CONFIG_GLOBAL": "/dev/null", "HOME": str(r), "PATH": "/usr/bin:/bin"}
        subprocess.run(["git", "-C", str(r), *a], check=True, capture_output=True, env=env)
    git("init", "-q", "-b", "main", name="x", email="x@x", date="2024-01-01T00:00:00")
    for i, (name, email) in enumerate([("Zed Zee", "zed@work.example")] * 4 + [("Zed Zee", "zed@home.example")] + [("Ann Lee", "ann@x.example")] * 2):
        (r / "shared.txt").write_text("\n".join(str(j) for j in range(i + 1)) + "\n")
        git("add", "-A", name=name, email=email, date=f"2024-01-{i+1:02d}T00:00:00")
        git("commit", "-qm", f"c{i}", name=name, email=email, date=f"2024-01-{i+1:02d}T00:00:00")
    db = tmp_path / "s.sqlite"
    build_index(r, db, now=__import__("datetime").datetime(2024, 2, 1, tzinfo=__import__("datetime").timezone.utc))
    with open_index(db) as ix:
        keys, note = resolve_person(ix, "Zed Zee")
        assert keys == {"zed@work.example", "zed@home.example"} and "merged" in note
        rep = person_report(ix, keys, now="2024-02-01")
    f = rep["top_files"]["built_it"][0]
    # Ann out-ranks Zed (Zed's creation is the root commit: no +3 under not_root); the point is that the report
    # takes Zed's 4-commit identity (rank 2), not the 1-commit one (rank 3)
    assert f["path"] == "shared.txt" and f["rank_built_it"] == 2
