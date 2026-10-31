"""A clean checkout is what the Docker build sees, so sources must not be gitignored."""

import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT = Path(__file__).parents[3]


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_no_source_file_is_ignored_by_git():
    listing = subprocess.run(
        ["git", "ls-files", "--others", "--ignored", "--exclude-standard", "--",
         "frontend/src", "frontend/package.json", "frontend/package-lock.json",
         "backend/app", "backend/tests", "backend/pyproject.toml", "backend/uv.lock", "test/e2e"],
        cwd=PROJECT, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    ignored = [path for path in listing if "__pycache__" not in path and not path.endswith(".pyc")]
    assert ignored == []
