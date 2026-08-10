"""The window opens a project that exists and walks it with the hotkey verbs.

One case, because the item this file answers is one capability: the app stands
up, a project on disk becomes an open session, and the three positions and the
node walk are reachable from the two pairs of keys. What each part looks like
is not asserted here — a skeleton that renders the wrong shade of grey is still
a skeleton, and the things worth pinning are the ones a later phase could break
without noticing: which position is current, how many ticks the rail drew, and
which node the step position is showing.

The keys themselves are not synthesized. `bind_navigation_hotkeys` wires four
`QShortcut`s to four window methods and holds no other opinion; driving the
methods tests the walk, and driving Qt's shortcut delivery through an offscreen
window with no focus would test Qt.

`sieve.gui` is imported inside the test rather than above it, for the reason
`conftest.py` gives: a module-scoped import here is executed during collection
and would put Qt in the process the headless loop budget is measured in.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, Project
from tests.gui import driving

_TOOLS = ("downsample", "crop", "detect")


@pytest.fixture
def project_file(tmp_path: Path) -> Path:
    """A three-node chain, rooted on no source at all.

    Nothing in this file decodes and nothing here needs footage: the skeleton
    renders whatever graph the document holds, and a graph with no source root
    is a document the schema admits (`adr/a-document-names-footage-only-through-
    a-tool.md`) rather than one the window has to refuse to draw.
    """
    project = Project(
        pipeline=Pipeline(
            nodes=tuple(
                Node(node_id=f"n{i}", tool_id=tool, version="1.0.0")
                for i, tool in enumerate(_TOOLS)
            ),
            edges=(Edge(upstream="n0", downstream="n1"), Edge(upstream="n1", downstream="n2")),
        ),
    )
    path = tmp_path / "clip.sieve.yaml"
    project.save(path)
    return path


def test_opens_a_project_and_walks_to_a_step(qapp, project_file: Path) -> None:
    from sieve.gui.app import MainWindow
    from sieve.gui.project_select import projects_in

    window = MainWindow(projects_in(project_file.parent))
    window.show()

    assert window.session is None
    assert window.control.current_position() == "project"

    driving.double_click(window.control.project_select.cards[0], 4.0, 4.0)

    assert window.session is not None
    assert window.session.path == project_file
    assert window.control.current_position() == "pipeline"
    assert window.control.rail.tick_count() == len(_TOOLS)
    assert window.current_node is not None
    assert window.current_node.node_id == "n0"

    window.go_down()
    assert window.current_node.node_id == "n1"
    assert window.control.current_position() == "pipeline"

    window.go_forward()
    assert window.control.current_position() == "step"
    assert window.control.step_pane.node.node_id == "n1"

    window.go_back()
    assert window.control.current_position() == "pipeline"
    window.go_back()
    assert window.control.current_position() == "project"
