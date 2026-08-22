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
