"""The `post-commit` stamp writes a usable hash, and stops after one commit.

Two claims carry the hook. The stamp itself must land as a *string* — the same
YAML octal that indexed `0707005` as 232965 is a live hazard every time a hash
is written by machine. And the stamp commit must not re-trigger the stamp: the
only thing terminating that recursion is that nothing in the second commit says
`pending`, which is a claim about `pending_entries`, not about the shim.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from stamp_commit import ENTRY_NAME, PENDING, message, pending_entries, stamp

ENTRY = """\
---
title: Something finished
date: 2026-08-05T18:18:57-07:00
commit: "pending"
tags: []

summary: >
  A sentence that happens to contain the word pending.

settled: none

files:
  added: []
  changed: []
  removed: []
---
"""


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway repo with one commit, wired in as `stamp_commit.REPO_ROOT`."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "docs" / "completed-todo").mkdir(parents=True)
    (tmp_path / "README.md").write_text("first\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "chore: first")
    monkeypatch.setattr("stamp_commit.REPO_ROOT", tmp_path)
    return tmp_path


class TestStamp:
    def test_hash_is_written_quoted(self, tmp_path: Path) -> None:
        """An all-digit or leading-zero hash must not become a YAML integer."""
        path = tmp_path / "entry.md"
        path.write_text(ENTRY, encoding="utf-8")
        assert stamp(path, "0707005")
        assert 'commit: "0707005"' in path.read_text(encoding="utf-8")

    def test_the_word_pending_in_prose_is_left_alone(self, tmp_path: Path) -> None:
        path = tmp_path / "entry.md"
        path.write_text(ENTRY, encoding="utf-8")
        stamp(path, "abc1234")
        assert "the word pending" in path.read_text(encoding="utf-8")
        assert not PENDING.search(path.read_text(encoding="utf-8"))


class TestPendingEntries:
    def test_finds_the_entry_the_commit_carried(self, repo: Path) -> None:
        entry = repo / "docs" / "completed-todo" / "2026.08.05-a-thing.md"
        entry.write_text(ENTRY, encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "feat: a thing")
        assert pending_entries() == [(entry, "a-thing")]

    def test_a_stamped_entry_ends_the_recursion(self, repo: Path) -> None:
        """The stamp commit touches the entry again and must find nothing."""
        entry = repo / "docs" / "completed-todo" / "2026.08.05-a-thing.md"
        entry.write_text(ENTRY, encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "feat: a thing")
        stamp(entry, _git(repo, "rev-parse", "--short", "HEAD").strip())
        _git(repo, "commit", "-qam", "docs(a-thing): stamp the entry with its commit")
        assert pending_entries() == []

    def test_an_older_pending_entry_is_not_claimed(self, repo: Path) -> None:
        """Stamping it with this commit would name a commit it does not describe."""
        entry = repo / "docs" / "completed-todo" / "2026.08.05-a-thing.md"
        entry.write_text(ENTRY, encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "feat: a thing")
        (repo / "README.md").write_text("second\n", encoding="utf-8")
        _git(repo, "commit", "-qam", "docs: unrelated")
        assert pending_entries() == []
        assert PENDING.search(entry.read_text(encoding="utf-8"))


class TestSubject:
    def test_one_entry_names_its_slug(self) -> None:
        assert message(["a-thing"]) == "docs(a-thing): stamp the entry with its commit"

    def test_several_entries_drop_the_scope(self) -> None:
        """No single item owns the commit, so no scope is guessed."""
        assert "(" not in message(["a-thing", "another-thing"])


class TestEntryName:
    @pytest.mark.parametrize(
        "name",
        ["2026.08.05-a-thing.md", "2026.12.31-x.md"],
    )
    def test_accepts_what_complete_item_mints(self, name: str) -> None:
        assert ENTRY_NAME.match(name)

    @pytest.mark.parametrize("name", [".index.md", "SETTLED.md", "a-thing.md"])
    def test_rejects_everything_else(self, name: str) -> None:
        assert ENTRY_NAME.match(name) is None
