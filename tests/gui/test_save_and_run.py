"""The checkoff writes the document's lists, and Run hands the file to the CLI.

The screen is built bare rather than reached through `MainWindow`, for
`test_kind_editors.py`'s reason: nothing in the tree places a Phase 7 surface
yet, and a checkoff read back through a window would leave open whether the
checkbox wrote it or the wiring did.

The two tools the checkoff runs against are declared and never registered, for
`test_param_generator.py`'s reason. One has a single product and one has two
chosen by an enum, because the list the screen offers is *every* product a node
could be asked for and a one-emission tool alone would let a screen that only
ever offers one row pass.

**The run is a real `sieve run`.** The point of the button is that the GUI issues
the command a cluster node would (`docs/VISION.md`, the handoff), and a test that
asserted only the argv would pass against a screen that never spawned anything.
That case runs a registered tool instead, so the CLI reads, resolves and plans
the document the GUI just wrote and stops at the one thing that is missing — the
footage — which is both a fixed sentence to assert on and the strongest available
statement that the artifact travelled.

**The last two cases are about the other write, and they need a window.** Run is
not the only thing that puts the document on disk any more — closing the window
is too — and that one cannot be driven against a bare screen, because the whole
of it is the wire between `MainWindow.closeEvent` and `Session.save_if_edited`.
They are here rather than in `test_app.py` because what they assert is what the
file holds afterwards, which is this module's subject.

Qt and `sieve.gui` are imported inside the test bodies, for the reason
`conftest.py` gives.
"""

from __future__ import annotations

import shutil
from enum import StrEnum
from pathlib import Path
from typing import Any

import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, Project, Sink
from sieve.core.tool_base import (
    ArraySpec,
    ElementRelation,
    Emission,
    ParamsBase,
    ParamStereotype,
    ToolSpec,
)
from sieve.core.tool_registry import REGISTRY
from sieve.session.session import Session
from sieve.tools import discover
from tests.gui import driving

#: How long the CLI is given to start, import typer and pydantic, refuse, and
#: exit. Generous because what a slow machine costs here is a flake, and what it
#: buys is nothing — the wait ends when the process does.
_RUN_TIMEOUT_MS = 60_000


class OneProductParams(ParamsBase):
    """A tool that computes one thing, so its row has nothing to choose."""

    count: int = 4


class Product(StrEnum):
    POWER = "power"
    PHASE = "phase"


class TwoProductParams(ParamsBase):
    """A tool whose enum picks which of two measurements leaves the node."""

    signal: Product = Product.POWER


def _specs() -> dict[str, ToolSpec]:
    one = ToolSpec(
        tool_id="one_product",
        version="1.0.0",
        summary="A tool with a single product.",
        params_model=OneProductParams,
        accepts=ArraySpec(),
        emits=ArraySpec(),
        emissions=(Emission("frames"),),
        element=ElementRelation.PRESERVED,
        param_stereotypes={"count": ParamStereotype.SCALAR_RANGE},
    )
    two = ToolSpec(
        tool_id="two_products",
        version="1.0.0",
        summary="A tool whose parameter picks the product.",
        params_model=TwoProductParams,
        accepts=ArraySpec(),
        emits=ArraySpec(),
        emissions=(Emission(Product.POWER, "signal"), Emission(Product.PHASE, "signal")),
        element=ElementRelation.PRESERVED,
        param_value_labels={"signal": {Product.POWER: "Power", Product.PHASE: "Phase"}},
        param_stereotypes={"signal": ParamStereotype.ENUM},
    )
    return {"n0": one, "n1": two}


def _project(**fields: Any) -> Project:
    """A two-node chain over footage that is deliberately not there."""
    return Project(
        pipeline=Pipeline(
            nodes=(
                Node(node_id="n0", tool_id="one_product", version="1.0.0"),
                Node(node_id="n1", tool_id="two_products", version="1.0.0"),
            ),
            edges=(Edge(upstream="n0", downstream="n1"),),
        ),
        **fields,
    )


def _named(screen: Any) -> list[tuple[str, str]]:
    return [(row.node_id, row.emission.name) for row in screen.rows]


def _checked(screen: Any) -> list[tuple[str, str]]:
    return [
        (row.node_id, row.emission.name) for row in screen.rows if screen.checkbox(row).isChecked()
    ]


def test_the_checkoff_writes_the_projects_lists(qapp, tmp_path: Path) -> None:
    del qapp
    from sieve.gui.save_screen import SaveScreen

    sink = Sink(node_id="n1", format="csv", path="out")
    project = _project(outputs=(sink,))
    session = Session(tmp_path / "clip.sieve.yaml", project)
    screen = SaveScreen(session, _specs())

    # Every product of every node, whatever the parameters currently select.
    assert _named(screen) == [("n0", "frames"), ("n1", "power"), ("n1", "phase")]
    assert _checked(screen) == []
    # The product is named in the tool's own words where it has any.
    assert screen.checkbox(screen.rows[1]).text() == "n1 — Power"

    screen.checkbox(screen.rows[1]).click()

    assert session.project.checkpoints == ("n1",)
    # The sinks are carried, not invented: nothing on this screen names a
    # format or a directory, and `SetOutputs` writes both lists at once.
    assert session.project.outputs == (sink,)
    # No cache key moved — the graph is the same graph.
    assert session.project.pipeline == project.pipeline

    screen.checkbox(screen.rows[0]).click()

    # Walk order, not click order.
    assert session.project.checkpoints == ("n0", "n1")

    screen.checkbox(screen.rows[1]).click()

    assert session.project.checkpoints == ("n0",)

    # A screen built on what the document now holds shows the same checkoff,
    # and shows it against the product the node's parameters select.
    assert _checked(SaveScreen(session, _specs())) == [("n0", "frames")]


def test_the_run_button_issues_the_cli_command(qapp, tmp_path: Path) -> None:
    del qapp
    from sieve.gui.save_screen import SaveScreen

    assert shutil.which("sieve") is not None, (
        "the run button spawns the console script by name, as a cluster node would; "
        "it is not on PATH in this environment"
    )
    path = tmp_path / "clip.sieve.yaml"
    # A registered tool and no source root, so what the CLI stops at is the
    # footage rather than the graph: the document the GUI saved is one it read
    # and resolved (`adr/a-document-names-footage-only-through-a-tool.md`).
    discover()
    spec = REGISTRY.latest("downsample")
    project = Project(
        pipeline=Pipeline(nodes=(Node(node_id="n0", tool_id=spec.tool_id, version=spec.version),)),
    )
    session = Session(path, project)
    screen = SaveScreen(session, {"n0": spec})
    issued: list[tuple[str, ...]] = []
    screen.run_issued.connect(issued.append)

    screen.checkbox(screen.rows[0]).click()
    screen.run_button.click()

    assert issued == [("sieve", "run", str(path))]
    # What was handed over is the file, not the value in memory.
    assert Project.load(path).checkpoints == ("n0",)

    driving.wait_until(lambda: not screen.running(), _RUN_TIMEOUT_MS)

    # The CLI's own words, surfaced rather than swallowed.
    assert "names no footage" in screen.message()


def test_a_second_click_while_a_run_is_in_flight_does_nothing(qapp, tmp_path: Path) -> None:
    """One button, one run. An impatient click is not a second handoff.

    Unguarded, the second click re-saves the document under the first run's feet,
    clears the message that run is about to write into, and emits `run_issued`
    for a process `QProcess` declines to start because one is already attached —
    three wrong answers, none of which the user would connect to having clicked
    twice.

    Driven against the real `sieve`, because what makes the window between the
    clicks real is a process that takes a beat to start and refuse; a program
    that does not exist reports `FailedToStart` and there is nothing in flight to
    click during.
    """
    del qapp
    from sieve.gui.save_screen import SaveScreen

    assert shutil.which("sieve") is not None, "the run button spawns the console script by name"
    path = tmp_path / "clip.sieve.yaml"
    discover()
    spec = REGISTRY.latest("downsample")
    project = Project(
        pipeline=Pipeline(nodes=(Node(node_id="n0", tool_id=spec.tool_id, version=spec.version),)),
    )
    session = Session(path, project)
    screen = SaveScreen(session, {"n0": spec})
    issued: list[tuple[str, ...]] = []
    screen.run_issued.connect(issued.append)

    screen.run_button.click()
    assert screen.running()
    screen.run_button.click()

    assert issued == [("sieve", "run", str(path))]

    driving.wait_until(lambda: not screen.running(), _RUN_TIMEOUT_MS)

    # And the one run that did start still reported, rather than having had its
    # message cleared out from under it.
    assert "names no footage" in screen.message()


def test_a_command_that_will_not_start_says_so(qapp, tmp_path: Path, monkeypatch) -> None:
    """The other way a run ends: no such program, and no `finished` to hear.

    A GUI installed without the console script on its PATH would otherwise sit
    silent after a click, which is the one failure the user cannot tell from a
    long run.
    """
    del qapp
    from sieve.gui import save_screen

    monkeypatch.setattr(save_screen, "CLI_PROGRAM", "sieve-that-is-not-installed")
    session = Session(tmp_path / "clip.sieve.yaml", _project())
    screen = save_screen.SaveScreen(session, _specs())

    screen.run_button.click()

    driving.wait_until(lambda: not screen.running(), _RUN_TIMEOUT_MS)

    assert "sieve-that-is-not-installed" in screen.message()


#: A hand-written line no `Project.to_yaml` would produce, appended to the file
#: the window is opened on. A rewrite of the document drops it, so it says that
#: the file was not rewritten rather than that it round-tripped to the same
#: bytes — which a comparison against a re-serialized project could not tell
#: apart.
_MARKER = b"# hand-written; a save would drop this line\n"


@pytest.fixture
def chain_file(tmp_path: Path) -> Path:
    """A two-step project on disk, over footage that is not there.

    Registered tools, because the window resolves specs off the shelf and a card
    for a tool this install lacks carries no ✕ (`app.removable`). The missing
    footage costs nothing: the transport fails on it asynchronously and neither
    case waits for a frame.
    """
    discover()
    spec = REGISTRY.latest("downsample")
    project = Project(
        pipeline=Pipeline(
            nodes=(
                Node(node_id="n0", tool_id=spec.tool_id, version=spec.version),
                Node(node_id="n1", tool_id=spec.tool_id, version=spec.version),
            ),
            edges=(Edge(upstream="n0", downstream="n1"),),
        ),
    )
    path = tmp_path / "clip.sieve.yaml"
    project.save(path)
    path.write_bytes(path.read_bytes() + _MARKER)
    return path


def test_an_edit_survives_a_close(qapp, chain_file: Path) -> None:
    """Drop a step, close the window, and the file is the chain that is left.

    A removal rather than a parameter, because it is the edit whose loss is
    least deniable: the document on disk would still name a step the user
    watched leave the stack, and the next `sieve run` would compute it.
    """
    del qapp
    from sieve.gui.app import MainWindow

    window = MainWindow([chain_file])
    try:
        window.open_project(chain_file)
        assert window.session is not None
        assert not window.session.edited

        window.remove_step(1)

        assert window.session.edited
        # Nothing has been written yet: the edit is the session's until the
        # gesture that saves, and this case exists because there was none.
        assert len(Project.load(chain_file).pipeline.nodes) == 2
    finally:
        window.close()

    saved = Project.load(chain_file)
    assert tuple(node.node_id for node in saved.pipeline.nodes) == ("n0",)
    assert saved.pipeline.edges == ()


def test_a_clean_document_writes_nothing(qapp, chain_file: Path) -> None:
    """Open a project, walk it, close it — and the file is untouched, byte for byte.

    The walk and the pin move on the way through, which is the point: they are
    view state and none of them is a change to the document (`app.py`), so the
    close has every opportunity to write and no reason to. That an edit made and
    undone is clean again is the same claim from the session's side, where the
    comparison lives (`tests/unit/test_session.py`).
    """
    del qapp
    from sieve.gui.app import MainWindow

    before = chain_file.read_bytes()
    window = MainWindow([chain_file])
    try:
        window.open_project(chain_file)
        assert window.session is not None
        # Really open, so that "nothing was written" is not "nothing happened".
        assert window.current_node is not None

        window.go_down()
        window.pin_current()

        assert not window.session.edited
    finally:
        window.close()

    assert chain_file.read_bytes() == before
