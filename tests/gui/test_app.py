"""What the window paints when the node under the walk owns a drawn rectangle.

`app.viewport_node` refuses to show a render for a source-fed node carrying a
`region` parameter, because that is the one case where an editor's box is on the
canvas: the value is denominated in the frame the node reads, and painting the
node's *output* would draw the box over a rectangle the value does not index
(`kind_editors.RegionEditor`). Every other case in the suite walks to the
detector on a graph whose `crop` is downstream of a `downsample`, so nothing ever
stands where that refusal is reachable.

Nothing here decodes. The source is a name the window resolves and hands to the
transport, which fails on it asynchronously; what is asserted is the decision
`viewport_node` makes from the document and the shelf, which is taken before any
frame arrives.

Qt and `sieve.gui` are imported inside the test, for the reason `conftest.py`
gives.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, Project, SourceRef

#: `crop` at the root, so its `region` is denominated in the footage, and one
#: node under it with no stereotype of its own — which is what separates "the
#: window has no picture to show" from "the window declines to show one".
_ROOT = "cut"
_BELOW = "smaller"


@pytest.fixture
def project_file(tmp_path: Path) -> Path:
    project = Project(
        source=SourceRef(path="clip.mp4"),
        pipeline=Pipeline(
            nodes=(
                Node(node_id=_ROOT, tool_id="crop", version="1.0.0"),
                Node(node_id=_BELOW, tool_id="downsample", version="1.0.0"),
            ),
            edges=(Edge(upstream=_ROOT, downstream=_BELOW),),
        ),
    )
    path = tmp_path / "clip.sieve.yaml"
    project.save(path)
    return path


def test_a_source_fed_region_node_keeps_the_source_on_the_canvas(qapp, project_file: Path) -> None:
    """The refusal, and the ordinary case that says the refusal is doing it.

    Standing on the second node is not decoration: `viewport_node` is `None` for
    a walk with no spec above it too, so a case asserting only the `None` would
    pass on a shelf that had never resolved `crop` at all.
    """
    del qapp
    from sieve.gui.app import MainWindow

    window = MainWindow([project_file])
    try:
        window.open_project(project_file)

        assert window.current_node is not None
        assert window.current_node.node_id == _ROOT
        assert window.viewport_node is None

        window.go_down()
        assert window.current_node.node_id == _BELOW
        assert window.viewport_node == _BELOW
    finally:
        window.close()
