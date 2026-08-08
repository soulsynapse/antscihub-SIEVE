"""The inherited state is this worktree's, and an untracked file is part of it.

Every case builds a real repository rather than mocking `git status`, because the
two claims worth pinning are git's own behaviour and not this module's arithmetic:
that a sibling worktree's dirt does not appear here, and that an untracked file
does. A stub would let either drift silently.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from inherited_changes import GitUnavailable, inherited, main


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository with one commit, so a modification has something to differ from."""
    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "-b", "main")
    git(work, "config", "user.email", "case@example.invalid")
    git(work, "config", "user.name", "Case")
    (work / "tracked.txt").write_text("first\n", encoding="utf-8")
    git(work, "add", "tracked.txt")
    git(work, "commit", "-m", "seed")
    return work


def test_a_clean_worktree_inherits_nothing(repo: Path) -> None:
    assert inherited(repo) == []
    assert main([], repo) == 0


def test_a_modified_file_is_inherited(repo: Path) -> None:
    (repo / "tracked.txt").write_text("second\n", encoding="utf-8")

    assert inherited(repo) == [" M tracked.txt"]
    assert main([], repo) == 1


def test_an_untracked_file_is_inherited(repo: Path) -> None:
    """`-A` sweeps up an untracked file, so a report that skipped one would miss
    the shape it exists to catch."""
    (repo / "scratch.txt").write_text("notes\n", encoding="utf-8")

    assert inherited(repo) == ["?? scratch.txt"]


def test_an_ignored_file_is_not_inherited(repo: Path) -> None:
    (repo / ".gitignore").write_text("*.log\n", encoding="utf-8")
    git(repo, "add", ".gitignore")
    git(repo, "commit", "-m", "ignore logs")
    (repo / "run.log").write_text("noise\n", encoding="utf-8")

    assert inherited(repo) == []


def test_a_sibling_worktrees_dirt_is_not_this_ones(repo: Path, tmp_path: Path) -> None:
    """The scope is the worktree, which is what makes the answer usable here: v3
    shares one `.git` with v2, so a repository-wide reading would report the other
    generation's uncommitted work as this run's to explain."""
    sibling = tmp_path / "sibling"
    git(repo, "worktree", "add", "-b", "other", str(sibling))
    (sibling / "tracked.txt").write_text("edited over there\n", encoding="utf-8")

    assert inherited(sibling) == [" M tracked.txt"]
    assert inherited(repo) == []


def test_a_directory_that_is_not_a_repository_is_refused(tmp_path: Path) -> None:
    """Unknown is not clean. Returning `[]` here would report the one tree whose
    state nothing can vouch for as the one tree that needs no report."""
    with pytest.raises(GitUnavailable):
        inherited(tmp_path)

    assert main([], tmp_path) == 2


def test_an_argument_is_refused(repo: Path) -> None:
    assert main(["--all"], repo) == 2
