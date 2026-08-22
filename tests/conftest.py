import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "fixtures"))
from build_fixture import build  # noqa: E402


@pytest.fixture(scope="session")
def fixture_repo(tmp_path_factory) -> Path:
    return build(tmp_path_factory.mktemp("fixture") / "repo")
