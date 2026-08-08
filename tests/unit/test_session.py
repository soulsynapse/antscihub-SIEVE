"""The open project and the two stacks around it.

Each case here stands in for a way history stops being a walk through whole
values: a step back that hands out something other than the value that stood
there, a redo branch that survives an edit made after the undo, or a project
that comes back off disk as a different document from the one the session was
holding when it saved.
"""

from __future__ import annotations

from pathlib import Path

from sieve.core.pipeline_model import Node, Pipeline, Project, SourceRef
from sieve.session.session import Session


def _project(level: float) -> Project:
    """A one-node project distinguishable only by the value under tuning."""
    return Project(
        source=SourceRef(path="arena.MP4"),
        pipeline=Pipeline(
            nodes=(
                Node(node_id="n1", tool_id="threshold", version="1.0.0", params={"level": level}),
            )
        ),
    )


def _opened(tmp_path: Path) -> Session:
    path = tmp_path / "arena.sieve.yaml"
    _project(0.25).save(path)
    return Session.open(path)


def test_a_freshly_opened_session_has_nothing_to_undo(tmp_path: Path) -> None:
    session = _opened(tmp_path)

    assert session.project == _project(0.25)
    assert not session.can_undo()
    assert not session.can_redo()


def test_undo_restores_the_prior_whole_value(tmp_path: Path) -> None:
    session = _opened(tmp_path)
    session.commit(_project(0.5))

    assert session.undo() == _project(0.25)
    assert session.project == _project(0.25)


def test_redo_returns_the_value_undone_away_from(tmp_path: Path) -> None:
    session = _opened(tmp_path)
    session.commit(_project(0.5))
    session.undo()

    assert session.redo() == _project(0.5)


def test_undo_with_nothing_committed_is_a_no_op(tmp_path: Path) -> None:
    session = _opened(tmp_path)

    assert session.undo() == _project(0.25)
    assert not session.can_undo()


def test_a_commit_after_an_undo_discards_the_redo_branch(tmp_path: Path) -> None:
    session = _opened(tmp_path)
    session.commit(_project(0.5))
    session.undo()
    session.commit(_project(0.75))

    assert not session.can_redo()
    assert session.project == _project(0.75)


def test_can_undo_and_can_redo_track_the_two_stacks(tmp_path: Path) -> None:
    session = _opened(tmp_path)
    assert not session.can_undo()
    assert not session.can_redo()

    session.commit(_project(0.5))
    assert session.can_undo()
    assert not session.can_redo()

    session.undo()
    assert not session.can_undo()
    assert session.can_redo()


def test_a_reopened_project_round_trips(tmp_path: Path) -> None:
    session = _opened(tmp_path)
    session.commit(_project(0.5))
    session.save()

    reopened = Session.open(session.path)

    assert reopened.project == session.project
    assert not reopened.can_undo()


def test_saving_after_an_undo_writes_the_restored_value(tmp_path: Path) -> None:
    session = _opened(tmp_path)
    session.commit(_project(0.5))
    session.undo()
    session.save()

    assert Session.open(session.path).project == _project(0.25)
