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

Qt and `sieve.gui` are imported inside the test bodies, for the reason
`conftest.py` gives.
"""

from __future__ import annotations

import shutil
from enum import StrEnum
from pathlib import Path
from typing import Any

from sieve.core.pipeline_model import Edge, Node, Pipeline, Project, Sink, SourceRef
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
        source=SourceRef(path="clip.mp4"),
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
    # A registered tool, so what the CLI stops at is the footage rather than the
    # graph: the document the GUI saved is one it read, resolved and planned.
    discover()
    spec = REGISTRY.latest("downsample")
    project = Project(
        source=SourceRef(path="clip.mp4"),
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
    assert "source video is not where the project says" in screen.message()


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
