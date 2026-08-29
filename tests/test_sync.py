from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import sync


def _result(
    *arguments: str,
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        ["git", *arguments],
        returncode,
        stdout,
        stderr,
    )


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("study_data/notes/first.md", True),
        (r"study_data\cards\abc.json", True),
        ("study_data", True),
        ("study_data_backup/file", False),
        ("app.py", False),
    ],
)
def test_is_study_path_is_boundary_aware(path: str, expected: bool) -> None:
    assert sync.is_study_path(path) is expected


def test_safe_state_rejects_unrelated_staged_changes(monkeypatch) -> None:
    def fake_paths(*arguments: str) -> list[str]:
        if "--diff-filter=U" in arguments:
            return []
        return ["study_data/notes/first.md", "app.py"]

    monkeypatch.setattr(sync, "git_paths", fake_paths)
    monkeypatch.setattr(
        sync,
        "run_git",
        lambda *arguments, **kwargs: _result(*arguments, stdout="origin/main\n"),
    )

    with pytest.raises(sync.SyncError, match="unrelated changes"):
        sync.ensure_safe_state()


def test_safe_state_requires_an_upstream(monkeypatch) -> None:
    monkeypatch.setattr(sync, "git_paths", lambda *arguments: [])
    monkeypatch.setattr(
        sync,
        "run_git",
        lambda *arguments, **kwargs: (
            _result(*arguments, returncode=1)
            if "@{upstream}" in arguments
            else _result(*arguments)
        ),
    )

    with pytest.raises(sync.SyncError, match="no upstream"):
        sync.ensure_safe_state()


def test_stage_study_data_uses_top_level_pathspec(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, ...]] = []
    (tmp_path / "study_data").mkdir()

    def fake_run(*arguments: str, **kwargs):
        calls.append(arguments)
        return _result(*arguments)

    monkeypatch.setattr(sync, "run_git", fake_run)

    sync.stage_study_data(tmp_path)

    assert (
        "add",
        "--all",
        "--",
        sync.STUDY_DATA_PATHSPEC,
    ) in calls
