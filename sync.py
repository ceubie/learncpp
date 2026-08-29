from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

STUDY_DATA_PREFIX = "study_data/"
STUDY_DATA_PATHSPEC = ":(top)study_data"


class SyncError(RuntimeError):
    """Raised when the guarded Git workflow cannot continue safely."""


def run_git(
    *arguments: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if check and result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SyncError(detail or f"git {' '.join(arguments)} failed")
    return result


def git_paths(*arguments: str) -> list[str]:
    result = run_git(*arguments)
    return [
        path.replace("\\", "/")
        for path in result.stdout.splitlines()
        if path.strip()
    ]


def is_study_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    return normalized == "study_data" or normalized.startswith(STUDY_DATA_PREFIX)


def ensure_safe_state() -> None:
    run_git("rev-parse", "--show-toplevel")
    conflicted = git_paths("diff", "--name-only", "--diff-filter=U")
    if conflicted:
        raise SyncError(
            "Resolve the current Git conflicts before syncing study data."
        )

    staged = git_paths("diff", "--cached", "--name-only")
    unrelated = [path for path in staged if not is_study_path(path)]
    if unrelated:
        formatted = "\n".join(f"  - {path}" for path in unrelated)
        raise SyncError(
            "Refusing to sync because unrelated changes are staged:\n"
            f"{formatted}\n"
            "Commit or unstage those changes first."
        )

    upstream = run_git(
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
        check=False,
    )
    if upstream.returncode:
        raise SyncError(
            "The current branch has no upstream. Push it with "
            "`git push -u origin HEAD` once, then rerun sync.py."
        )


def stage_study_data(root: Path) -> None:
    tracked = run_git(
        "ls-files",
        "--",
        STUDY_DATA_PATHSPEC,
        check=False,
    ).stdout.strip()
    if root.joinpath("study_data").exists() or tracked:
        run_git("add", "--all", "--", STUDY_DATA_PATHSPEC)


def sync(message: str) -> None:
    root = Path(run_git("rev-parse", "--show-toplevel").stdout.strip())
    ensure_safe_state()
    stage_study_data(root)

    staged_study_changes = git_paths(
        "diff",
        "--cached",
        "--name-only",
        "--",
        STUDY_DATA_PATHSPEC,
    )
    if staged_study_changes:
        run_git("commit", "-m", message)
        print(f"Committed {len(staged_study_changes)} study data change(s).")
    else:
        print("No local study data changes to commit.")

    pull = run_git("pull", "--rebase", check=False)
    if pull.returncode:
        detail = pull.stderr.strip() or pull.stdout.strip()
        raise SyncError(
            "The rebase stopped. No automatic conflict resolution was attempted.\n"
            f"{detail}\n"
            "Resolve the conflict, continue or abort the rebase, then rerun sync.py."
        )

    run_git("push")
    print("Study data is synchronized.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Commit, rebase, and push only tracked LearnCpp study data."
    )
    parser.add_argument(
        "--message",
        default=f"Study C++ ({date.today().isoformat()})",
        help="Commit message used when study_data changed.",
    )
    args = parser.parse_args()

    try:
        sync(args.message)
    except SyncError as exc:
        print(f"Sync stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
