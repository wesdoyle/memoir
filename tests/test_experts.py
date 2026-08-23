"""memoir experts: ranked people over a set of files (dir / glob / match / explicit list)."""

import json

from typer.testing import CliRunner

from memoir.cli import app
from memoir.experts import experts_report, select_files
from memoir.index import default_index_path, open_index

runner = CliRunner()


def run(*args, input=None):
    r = runner.invoke(app, list(args), input=input, catch_exceptions=False)
    assert r.exit_code == 0, r.output
    return r.output


def _names(lst):
    return [e["name"] for e in lst]


def test_selectors(fixture_repo):
    run("index", "--repo", str(fixture_repo))
    with open_index(default_index_path(fixture_repo)) as ix:
        assert set(select_files(ix, dir="src")[0]) == {"src/core.py", "src/helpers.py"}
        assert select_files(ix, glob="*.md")[0] == ["README.md"]
        assert select_files(ix, match=["core"])[0] == ["src/core.py"]
        assert select_files(ix, match=["help"], prefix=True)[0] == ["src/helpers.py"]
        assert select_files(ix, files=["src/core.py", "nope.txt"])[0] == ["src/core.py"]
        paths, desc = select_files(ix, dir="src", match=["core"])  # selectors AND together
        assert paths == ["src/core.py"] and "src" in desc and "core" in desc


def test_experts_over_a_directory(fixture_repo):
    with open_index(default_index_path(fixture_repo)) as ix:
        rep = experts_report(ix, ["src/core.py", "src/helpers.py"], now="2026-08-21")
    assert rep["selection"]["files"] == 2
    cur, built = _names(rep["current"]), _names(rep["built_it"])
    assert set(cur[:2]) == {"Alice Adams", "Bob Smith"}  # each is #1 on one file
    assert "Carol Chen" in cur  # sweep: present, weaker
    assert set(built[:2]) == {"Alice Adams", "Bob Smith"}
    assert rep["current"][0]["files_top3"] >= 1 and rep["current"][0]["mass"] > 0


def test_tiny_selection_is_flagged(fixture_repo):
    with open_index(default_index_path(fixture_repo)) as ix:
        rep = experts_report(ix, ["src/core.py"], now="2026-08-21")
    assert rep["note"] and "who" in rep["note"]


def test_cli_text_json_and_stdin(fixture_repo):
    out = run("experts", "--dir", "src", "--repo", str(fixture_repo), "--now", "2026-08-21")
    assert "2 files" in out and "Alice Adams" in out and "Bob Smith" in out and "built_it" in out
    assert "mass" not in out  # an opaque number; JSON keeps it as the sortable
    data = json.loads(run("experts", "--match", "core", "--repo", str(fixture_repo), "--now", "2026-08-21", "--json"))
    assert data["selection"]["files"] == 1 and _names(data["current"])[0] == "Alice Adams"
    out = run("experts", "--files", "-", "--repo", str(fixture_repo), "--now", "2026-08-21", input="src/helpers.py\n")
    assert "Bob Smith" in out
    empty = runner.invoke(app, ["experts", "--match", "zzz", "--repo", str(fixture_repo)])
    assert empty.exit_code != 0 and "no files" in empty.output
