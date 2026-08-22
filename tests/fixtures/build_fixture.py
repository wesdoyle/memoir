"""Build a tiny synthetic git repository with known history for tests.

Deterministic: fixed authors, dates, and contents. Rebuild with

    uv run python tests/fixtures/build_fixture.py <dest-dir>

History (chronological; see EXPECTED below for what tests rely on):

  c01 2023-01-10 alice   create src/core.py, requirements.txt, README.md, .mailmap
  c02 2023-02-01 bob     create src/util.py
  c03 2023-03-05 alice   edit core.py
  c04 2023-04-12 alice   edit core.py, Co-authored-by: dave
  c05 2023-05-20 "Robert B" <rob@old.example>  edit util.py   (mailmap alias of bob)
  c06 2023-06-15 bob     pure rename src/util.py -> src/helpers.py
  c07 2023-07-01 alice   edit core.py
  c08 2023-08-01 dependabot[bot]  bump requirements.txt, Co-authored-by: dave
  c09 2023-10-01 dave    edit helpers.py on branch feature/dave
  c10 2023-10-05 alice   merge feature/dave (--no-ff; pure merge commit, no diff of its own)
  c11 2024-01-15 alice   edit core.py
  c12 2024-03-01 carol   lint sweep: reformat core.py, helpers.py, README.md (last touch on all three)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ALICE = ("Alice Adams", "alice@example.com")
BOB = ("Bob Smith", "bob@example.com")
BOB_ALIAS = ("Robert B", "rob@old.example")
CAROL = ("Carol Chen", "carol@example.com")
DAVE = ("Dave Diaz", "dave@example.com")
BOT = ("dependabot[bot]", "49699333+dependabot[bot]@users.noreply.github.com")

# Facts tests may assert on.
EXPECTED = {
    "core_creator": ALICE,
    "core_last_committer": CAROL,
    "helpers_creator": BOB,
    "helpers_old_path": "src/util.py",
    "mailmap_alias_of_bob": BOB_ALIAS,
    "bot": BOT,
    "coauthor_of_c04": DAVE,
    "commit_count_main": 12,
}


def _git(repo: Path, *args: str, author: tuple[str, str], date: str, extra_env: dict | None = None) -> str:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": author[0],
            "GIT_AUTHOR_EMAIL": author[1],
            "GIT_COMMITTER_NAME": author[0],
            "GIT_COMMITTER_EMAIL": author[1],
            "GIT_AUTHOR_DATE": f"{date}T12:00:00+00:00",
            "GIT_COMMITTER_DATE": f"{date}T12:00:00+00:00",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "HOME": str(repo),  # ignore user-level git config (signing, hooks)
        }
    )
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["git", *args], cwd=repo, env=env, check=True, capture_output=True, text=True
    ).stdout


def _write(repo: Path, rel: str, text: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def _core(n_funcs: int, style: str = "double") -> str:
    q = '"' if style == "double" else "'"
    lines = [f"{q}{q}{q}Core module.{q}{q}{q}", ""]
    for i in range(n_funcs):
        lines += [f"def f{i}(x):", f"    return x + {i}  # {q}f{i}{q}", ""]
    return "\n".join(lines) + "\n"


def _helpers(n: int, style: str = "double") -> str:
    q = '"' if style == "double" else "'"
    lines = [f"{q}{q}{q}Helpers.{q}{q}{q}", ""]
    for i in range(n):
        lines += [f"def h{i}():", f"    return {q}h{i}{q}", ""]
    return "\n".join(lines) + "\n"


def build(dest: Path) -> Path:
    """Create the fixture repo at `dest` (must not exist or be empty). Returns dest."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    if any(dest.iterdir()):
        raise SystemExit(f"refusing to build into non-empty dir: {dest}")

    def commit(author, date, msg, *paths, all_=False, extra_env=None):
        if all_:
            _git(dest, "add", "-A", author=author, date=date)
        else:
            _git(dest, "add", *paths, author=author, date=date)
        _git(dest, "commit", "-q", "-m", msg, author=author, date=date, extra_env=extra_env)

    _git(dest, "init", "-q", "-b", "main", author=ALICE, date="2023-01-10")
    _git(dest, "config", "commit.gpgsign", "false", author=ALICE, date="2023-01-10")

    # c01
    _write(dest, "src/core.py", _core(8))
    _write(dest, "requirements.txt", "requests==2.28.0\n")
    _write(dest, "README.md", "# fixture\n\nA tiny project.\n")
    _write(dest, ".mailmap", f"{BOB[0]} <{BOB[1]}> {BOB_ALIAS[0]} <{BOB_ALIAS[1]}>\n")
    commit(ALICE, "2023-01-10", "Initial core module", all_=True)

    # c02
    _write(dest, "src/util.py", _helpers(4))
    commit(BOB, "2023-02-01", "Add util helpers", "src/util.py")

    # c03
    _write(dest, "src/core.py", _core(10))
    commit(ALICE, "2023-03-05", "core: add f8, f9", "src/core.py")

    # c04 (co-authored)
    _write(dest, "src/core.py", _core(12))
    commit(
        ALICE, "2023-04-12",
        f"core: add f10, f11\n\nCo-authored-by: {DAVE[0]} <{DAVE[1]}>",
        "src/core.py",
    )

    # c05 (bob under alias identity)
    _write(dest, "src/util.py", _helpers(5))
    commit(BOB_ALIAS, "2023-05-20", "util: add h4", "src/util.py")

    # c06 (pure rename)
    _git(dest, "mv", "src/util.py", "src/helpers.py", author=BOB, date="2023-06-15")
    commit(BOB, "2023-06-15", "Rename util -> helpers", all_=True)

    # c07
    _write(dest, "src/core.py", _core(13))
    commit(ALICE, "2023-07-01", "core: add f12", "src/core.py")

    # c08 (bot)
    _write(dest, "requirements.txt", "requests==2.31.0\n")
    commit(BOT, "2023-08-01", f"Bump requests from 2.28.0 to 2.31.0\n\nCo-authored-by: {DAVE[0]} <{DAVE[1]}>", "requirements.txt")

    # c09 on branch + c10 merge
    _git(dest, "checkout", "-q", "-b", "feature/dave", author=DAVE, date="2023-10-01")
    _write(dest, "src/helpers.py", _helpers(7))
    commit(DAVE, "2023-10-01", "helpers: add h5, h6", "src/helpers.py")
    _git(dest, "checkout", "-q", "main", author=ALICE, date="2023-10-05")
    _git(dest, "merge", "-q", "--no-ff", "-m", "Merge branch 'feature/dave'", "feature/dave",
         author=ALICE, date="2023-10-05")

    # c11
    _write(dest, "src/core.py", _core(14))
    commit(ALICE, "2024-01-15", "core: add f13", "src/core.py")

    # c12 (lint sweep by non-expert: every line with a quote changes)
    _write(dest, "src/core.py", _core(14, style="single"))
    _write(dest, "src/helpers.py", _helpers(7, style="single"))
    _write(dest, "README.md", "# fixture\n\nA tiny project.\n\nFormatted.\n")
    commit(CAROL, "2024-03-01", "style: prefer single quotes", all_=True)

    return dest


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(build(Path(sys.argv[1])))
