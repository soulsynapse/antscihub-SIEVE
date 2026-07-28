"""The session hooks stay quiet unless they have something to say.

A hook fires with no explanation attached and no user asking for it, so the
failure that matters is not "it crashed" — it is "it spoke every turn and got
ignored on the turn it mattered", and "it errored on a fresh clone". Both are
about silence, so both are what these pin.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from session_hooks import main, primer, tree


def _fake_git(responses: dict[tuple[str, ...], str]) -> Callable[..., str]:
    """Unlisted calls return `""` — the real `_git`'s failure path, so an
    unanticipated call reads as a git failure and not a harness error."""

    def fake(*args: str) -> str:
        return responses.get(args, "")

    return fake


def test_the_primer_is_silent_when_the_state_file_has_never_been_generated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A fresh clone before the first `nox -s docs` is legitimate. A session
    # that opens with an error about its own primer has been made worse.
    monkeypatch.setattr("session_hooks.REPO_ROOT", tmp_path)
    assert primer() == {}


def test_the_primer_carries_the_state_file_and_says_where_it_came_from(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state = tmp_path / "docs" / ".state.md"
    state.parent.mkdir(parents=True)
    state.write_text("**Open items (2)**\n", encoding="utf-8")
    monkeypatch.setattr("session_hooks.REPO_ROOT", tmp_path)

    context = cast(dict[str, str], primer()["hookSpecificOutput"])
    assert context["hookEventName"] == "SessionStart"
    body = context["additionalContext"]
    assert "**Open items (2)**" in body
    # Unattributed context is context a session cannot check or regenerate.
    assert "docs/.state.md" in body
    assert "nox -s docs" in body


def test_the_tree_report_says_nothing_when_there_is_nothing_to_say(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("session_hooks._git", _fake_git({}))
    assert tree() == {}


def test_the_tree_report_counts_dirt_and_unpushed_commits_separately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # They are different mistakes: one loses work to a stray checkout, the
    # other lets "committed" be read as "done". Collapsing them to one number
    # would say neither.
    responses = {
        ("status", "--short"): " M a.py\n?? b.py\n",
        ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): "origin/main\n",
        ("log", "--oneline", "@{u}..HEAD"): "aaa one\nbbb two\nccc three\n",
    }
    monkeypatch.setattr("session_hooks._git", _fake_git(responses))

    message = str(tree()["systemMessage"])
    assert "2 uncommitted" in message
    assert "a.py" in message and "b.py" in message
    assert "3 commits not pushed" in message


def test_a_branch_with_no_upstream_is_not_reported_as_entirely_unpushed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # `git log @{u}..HEAD` fails without an upstream and `_git` swallows it to
    # "", so this passes by construction today — it is here because the
    # tempting fix (fall back to `origin/main..HEAD`) reports every commit on
    # a new branch and would make the hook noise on exactly the branches where
    # work happens.
    monkeypatch.setattr("session_hooks._git", _fake_git({}))
    assert tree() == {}


def test_an_unknown_subcommand_fails_loudly(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["nonsense"]) == 2
    assert "usage" in capsys.readouterr().err


def test_the_commands_emit_parseable_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    responses = {("status", "--short"): " M a.py\n"}
    monkeypatch.setattr("session_hooks._git", _fake_git(responses))
    assert main(["tree"]) == 0
    assert "systemMessage" in json.loads(capsys.readouterr().out)
