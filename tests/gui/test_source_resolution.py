"""What the window believes the document's sources name, and when it re-asks.

VISION's new-project scenario drops a second video into the folder a source
param names, and has the user come back to SIEVE to find "two files now show in
the source tool". Coming back is the first input in the product that is neither
a user gesture nor a run, and it is what makes the resolution a thing that can
be *stale*: the document did not move, the graph did not move, and the answer
changed anyway.

Both legs are here because the trigger is a predicate and not an event. A window
that re-read on every activation change would re-read on the way out as well as
on the way in, which is a claim about when the answer can have moved that is
false in one direction — nothing changed on disk between the user leaving and
the window hearing that they left.

The project names no footage of its own, so nothing here opens a decoder: the
resolution stats and lists, and the files below are the names rather than
pictures (`todo/a-source-param-names-a-folder-and-several-files-are-an-ordering.md`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sieve.core.pipeline_model import Node, Pipeline, Project
from sieve.tools import discover
from tests.gui import driving

_SOURCE = "clips"


@pytest.fixture
def folder_project(tmp_path: Path) -> tuple[Path, Path]:
    """A project whose one node reads a folder holding one file."""
    folder = tmp_path / "arena"
    folder.mkdir()
    (folder / "a_first.mp4").write_bytes(b"")
    path = tmp_path / "folder.sieve.yaml"
    Project(
        pipeline=Pipeline(
            nodes=(
                Node(
                    node_id=_SOURCE,
                    tool_id="footage",
                    version="1.0.0",
                    params={"path": str(folder)},
                ),
            ),
            edges=(),
        )
    ).save(path)
    return path, folder


def _named(window: object) -> list[str]:
    return [path.name for path in window.resolved_sources[_SOURCE]]  # type: ignore[attr-defined]


def test_a_resolution_goes_stale_when_the_folder_changes(
    qapp, folder_project: tuple[Path, Path]
) -> None:
    """It goes stale, it stays stale while the window is away, and coming back clears it."""
    del qapp
    discover()
    from sieve.gui.app import MainWindow

    path, folder = folder_project
    window = MainWindow([path])
    try:
        window.open_project(path)
        assert _named(window) == ["a_first.mp4"]

        (folder / "b_second.mp4").write_bytes(b"")
        assert _named(window) == ["a_first.mp4"], "nothing on disk announces itself"

        driving.activation_change(window)
        assert _named(window) == ["a_first.mp4"], "a window that is not the active one is away"

        driving.activate(window)

        assert _named(window) == ["a_first.mp4", "b_second.mp4"]
    finally:
        driving.activate(window, active=False)
        window.close()
