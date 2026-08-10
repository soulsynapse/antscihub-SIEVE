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


def test_an_undo_back_to_the_saved_value_is_not_an_edit(tmp_path: Path) -> None:
    """`edited` is the comparison, not a flag a commit sets.

    A parameter moved and moved back leaves a session with two stacks and a
    document identical to the file's — and a close that wrote it anyway would
    be spending the stable serialization on a project nobody changed
    (`Session.save_if_edited`).
    """
    session = _opened(tmp_path)
    assert not session.edited

    session.commit(_project(0.5))
    assert session.edited

    session.undo()
    assert not session.edited


def test_a_session_over_a_file_it_has_not_read_is_edited(tmp_path: Path) -> None:
    """A project composed in memory is owed a write, and its path may hold nothing.

    The one case where the comparison has no left-hand side. Treating an unread
    file as agreeing would decline the only write that could make it true.
    """
    path = tmp_path / "arena.sieve.yaml"
    session = Session(path, _project(0.25))

    assert session.edited
    assert session.save_if_edited()
    assert Session.open(path).project == _project(0.25)


def test_a_save_is_not_repeated_for_a_document_that_has_not_moved(tmp_path: Path) -> None:
    session = _opened(tmp_path)
    session.commit(_project(0.5))

    assert session.save_if_edited()
    assert not session.save_if_edited()
    assert Session.open(session.path).project == _project(0.5)
