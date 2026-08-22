"""Rename forms emitted by git --numstat."""

import pytest

from memoir.mining import _numstat_path


@pytest.mark.parametrize("raw,expected", [
    ("src/util.py => src/helpers.py", "src/helpers.py"),
    ("src/{util.py => helpers.py}", "src/helpers.py"),
    ("a/{old => new}/f.py", "a/new/f.py"),
    ("a/{rpc => }/jobmaster/J.java", "a/jobmaster/J.java"),
    ("a/{ => rpc}/jobmaster/J.java", "a/rpc/jobmaster/J.java"),
    ("plain/path.py", "plain/path.py"),
])
def test_numstat_path(raw, expected):
    assert _numstat_path(raw) == expected
