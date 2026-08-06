"""The gate says whether it passed, and which stage did not.

`nox -s checks` is read through a `| tail -n`, because the full output is
thousands of lines. nox's own report goes to stderr, so that read used to end
on pytest's last progress line and say nothing at all. What these pin is the
one line a reader is left holding: that it exists on both paths, that it is
last, and that a failure in one stage cannot be mistaken for a failure in
another.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

import nox
import pytest
from nox.command import CommandFailed

from noxfile import CHECK_STAGES, run_check_stages

STAGE_NAMES = [name for name, _ in CHECK_STAGES]

# Never dereferenced: every stage here is a fake that ignores it.
_SESSION = cast(nox.Session, object())


def _ok(_: nox.Session) -> None:
    return None


def _boom(_: nox.Session) -> None:
    raise CommandFailed("forced")


def _stages(
    failing: str | None,
) -> tuple[list[str], list[tuple[str, Callable[[nox.Session], None]]]]:
    """The real stage names, with `failing` swapped for a raising stub. `ran`
    records arrivals, so a stage skipped after a failure is visible."""
    ran: list[str] = []

    def wrap(name: str) -> Callable[[nox.Session], None]:
        body = _boom if name == failing else _ok

        def stage(session: nox.Session) -> None:
            ran.append(name)
            body(session)

        return stage

    return ran, [(name, wrap(name)) for name in STAGE_NAMES]


@pytest.mark.parametrize("failing", STAGE_NAMES)
def test_each_stage_fails_with_its_own_name(failing: str) -> None:
    ran, stages = _stages(failing)
    lines: list[str] = []

    with pytest.raises(CommandFailed):
        run_check_stages(_SESSION, stages, lines.append)

    # One line, naming this stage and no other — the distinguishability the
    # whole change exists for.
    assert lines == [f"checks: FAIL ({failing})"]
    assert ran == STAGE_NAMES[: STAGE_NAMES.index(failing) + 1]


def test_the_pass_path_says_so() -> None:
    ran, stages = _stages(None)
    lines: list[str] = []

    run_check_stages(_SESSION, stages, lines.append)

    assert lines == ["checks: pass"]
    assert ran == STAGE_NAMES


def test_stage_names_are_the_sessions_they_run() -> None:
    """The verdict names a stage a reader is meant to go and re-run. A table
    whose labels drifted off its callables would name the wrong one."""
    assert [name for name, _ in CHECK_STAGES] == [stage.__name__ for _, stage in CHECK_STAGES]
