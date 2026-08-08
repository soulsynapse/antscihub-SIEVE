"""What a run inherited: uncommitted changes present before it wrote anything.

A run that stages by `git add -A` commits the tree it found, not the work it did.
02.1's work run did exactly that and shipped a hand edit to `CLAUDE.md` under its
own authorship, under a message about something else
(`docs/findings/loop/2026.08.07-git-add--a-commits-the-tree-the-run-inherited-not-the-work-it-did.md`).
The commit log is the only durable record of who decided what, and that failure
moves it in the direction nobody checks: a human's decision attributed to an agent.

Staging by explicit path is the instruction half and lives in `CLAUDE.md`. This is
the other half — a run says at its start what was already there, so the reviewer
reading the transcript can tell an inherited change from an authored one, and so a
human's in-progress edit survives a queued session instead of being swept into it.

Anything uncommitted at a run's start is inherited by definition: the run has not
written yet. So there is no notion of an *expected* change here and no allowlist to
drift — the question is only whether the tree was clean, and the answer is the
porcelain lines verbatim, which are what the run pastes.

Scope is the worktree, not the repository, and that is `git status`'s own doing
rather than a filter here: this directory is one worktree of a `.git` it shares
with v2, and status reports the tree it is run in. A test pins it, because the
sharing is what makes the wrong scope plausible.

    uv run python scripts/inherited_changes.py

Exit is 0 when the tree is clean and 1 when it is not. Non-zero is not a failure to
stop for — it is the run's cue to name what it found before it starts working.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class GitUnavailable(RuntimeError):
    """`git status` could not answer, so the tree's state is unknown."""


def inherited(repo: Path = REPO) -> list[str]:
    """The porcelain lines for `repo`'s worktree, in git's own order.

    `--porcelain` already carries the two properties this wants: untracked files
    are listed, because an inherited untracked file is precisely what `-A` sweeps
    up, and ignored ones are not, because those are nobody's edit.
    """
    finished = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if finished.returncode != 0:
        raise GitUnavailable(finished.stderr.strip() or "git status failed")
    return [line for line in finished.stdout.splitlines() if line.strip()]


def main(argv: list[str] | None = None, repo: Path = REPO) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        print(f"inherited_changes: takes no arguments, got {argv}", file=sys.stderr)
        return 2

    try:
        lines = inherited(repo)
    except GitUnavailable as error:
        print(f"inherited_changes: {error}", file=sys.stderr)
        return 2

    if not lines:
        print("inherited_changes: the worktree is clean")
        return 0
    for line in lines:
        print(line)
    print(
        f"inherited_changes: {len(lines)} uncommitted change(s) this run did not make — "
        f"name them before working, stage by explicit path, and leave them where they are"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
