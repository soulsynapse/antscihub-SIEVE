"""The three gestures that act on the region the fan has selected.

`test_crop_fan.py` holds the picture — where the squares stand and which one the
continuing arrow leaves. What is under test here is that the selection means
something: the + and − on the card change the document's replicates, and a knob
turned anywhere in the chain writes at that region's address rather than at the
project's baseline.

Each case is a way the selection could be decorative. That adding selects, so
the region a user just made is the one they are about to place, and that it
arrives carrying a box of its own rather than following the baseline the next
edit will move. That dropping *moves* the selection down with it — `RegionFan`
indexes its tiles by that number inside `paintEvent`, where an IndexError is
thrown through a Qt virtual override and aborts the process rather than raising,
so a stale number is not a stale picture. That the last region may go, because a
project with no replicates is the baseline run once and is the state every
document is minted in. And that a knob edits the showing region's own value,
which is what makes two regions two configurations rather than two labels on
one — with the other arm beside it, because a project with no regions has only
a baseline for an edit to be about.

The last case is where the verbs are offered at all: the row hangs on the step
whose box the regions are deviations of, and that step has to be one handed a
source frame — a region is denominated in the frame its own node reads
(`gui/kind_editors.RegionEditor`), so a fan under a node reading a reshaped one
would key overrides in a space nothing in the window can name.

The box drawn on the canvas is the same claim on the other surface, and it is
`test_kind_editors.py`'s: the overlay is built bare there, where a viewport
showing a frame does not need a decode thread to have delivered one.

**The last case decodes, because a selection that reaches the document and not
the render is decorative in the way that matters most.** Every case above reads
the document back; a preview aimed at the baseline while the fan stands on a
region would pass all of them and still put the neighbouring region's pixels on
the canvas. So it is asserted where it is visible — two regions deviating at the
crop's own box, over footage textured enough that two boxes of one frame are two
different pictures, with the render taken from the loop the window fills its
surfaces from.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, Project, Replicate
from sieve.pipeline.resolve_source import anchored
from tests.gui import driving
from tests.projects import over

#: A box on the footage, in source pixels. Small enough that a second region
#: copied from it is visibly the same rectangle rather than the whole frame.
_BOX = {"x": 10, "y": 20, "width": 100, "height": 80}

#: The two placed regions of the rendering case, in source pixels. The same size
#: so the two renders are comparable pixel for pixel rather than by shape, and
#: over the two corners `stirred_clip` textures differently.
_NORTH = {"x": 0, "y": 0, "width": 80, "height": 64}
_SOUTH = {"x": 80, "y": 56, "width": 80, "height": 64}

#: How long the decode thread is given to open the clip. `test_app.py`'s number
#: and its reason: the wait ends when the thing it waits on does, so a generous
#: ceiling costs nothing but the flake it prevents.
_TIMEOUT_MS = 60_000


def _project(tools: Sequence[str], replicates: tuple[Replicate, ...], **params: Any) -> Project:
    return Project(
        pipeline=Pipeline(
            nodes=tuple(
                Node(
                    node_id=f"n{position}",
                    tool_id=tool,
                    version="1.0.0",
                    params=params.get(f"n{position}", {}),
                )
                for position, tool in enumerate(tools)
            ),
            edges=tuple(
                Edge(upstream=f"n{position}", downstream=f"n{position + 1}")
                for position in range(len(tools) - 1)
            ),
        ),
        replicates=replicates,
    )


def _saved(path: Path, project: Project) -> Path:
    project.save(path)
    return path


def _window(path: Path) -> Iterator[Any]:
    from sieve.gui.app import MainWindow
    from sieve.gui.project_select import projects_in

    opened = MainWindow(projects_in(path.parent))
    opened.open_project(path)
    yield opened
    opened.close()


@pytest.fixture
def window(qapp, tmp_path: Path) -> Iterator[Any]:
    """`crop -> downsample -> detect` over two regions, the crop at the root."""
    del qapp
    yield from _window(
        _saved(
            tmp_path / "arena.sieve.yaml",
            _project(
                ("crop", "downsample", "detect"),
                (Replicate(name="north"), Replicate(name="south")),
            ),
        )
    )


def _row(window: Any, position: int = 0) -> Any:
    return window.control.pipeline_pane.cards[position].regions


def _knobs(window: Any, position: int) -> Any:
    from sieve.gui.param_form import ParamForm

    return window.control.pipeline_pane.cards[position].findChild(ParamForm)


def _ids(window: Any) -> list[str]:
    return [replicate.replicate_id for replicate in window.session.project.replicates]


def test_adding_a_region_selects_it(window: Any) -> None:
    _row(window).add.click()
    driving.pump()

    # The count is the document's and the selection is the window's, and the
    # gesture moved both: a + that left the walk where it was would make placing
    # the new region a second gesture the surface never asked for.
    assert len(window.session.project.replicates) == 3
    assert window.region == 2
    assert window.control.pipeline_pane.fan.selected == 2
    assert _row(window).count.text() == "3 regions · showing 3"


def test_a_new_region_carries_the_box_the_showing_one_was_placed_at(qapp, tmp_path: Path) -> None:
    del qapp
    placed = Replicate(name="north", overrides={"n0": {"region": _BOX}})
    path = _saved(
        tmp_path / "arena.sieve.yaml",
        _project(("crop", "downsample", "detect"), (placed,)),
    )
    for window in _window(path):
        _row(window).add.click()
        driving.pump()

        # Pinned rather than left to follow: the baseline is what the next edit
        # to either region moves (`Project.with_param_edit`), so an unpinned
        # arrival would be dragged along by the drag that placed its sibling and
        # the user would find a region they never touched under the one they did.
        project = window.session.project
        assert project.replicates[1].overrides["n0"]["region"] == _BOX
        assert project.params_for("n0", _ids(window)[1])["region"] == _BOX


def test_dropping_the_region_showing_moves_the_selection_off_it(window: Any) -> None:
    window.select_region(1)

    _row(window).drop.click()
    driving.pump()

    # Not a stale picture: `RegionFan.paintEvent` indexes its tiles by this
    # number, and an IndexError raised inside a Qt virtual override takes the
    # process down. The verb that makes the count able to shrink is the verb
    # that has to move it.
    assert [replicate.name for replicate in window.session.project.replicates] == ["north"]
    assert window.region == 0
    assert window.control.pipeline_pane.fan.selected == 0


def test_dropping_the_last_region_leaves_the_baseline_and_the_way_back(window: Any) -> None:
    _row(window).drop.click()
    _row(window).drop.click()
    driving.pump()

    # A project with no regions is what every document is minted as, so − has no
    # floor — and the row stays on the card at zero, because it is where the +
    # that gets a branch back is pressed.
    assert window.session.project.replicates == ()
    assert window.region == 0
    assert window.control.pipeline_pane.fan is None
    assert _row(window).count.text() == "no regions · the step's own box, once"
    assert not _row(window).drop.isEnabled()
    assert _row(window).add.isEnabled()


def test_a_knob_edits_the_selected_regions_own_value(window: Any) -> None:
    first, second = _ids(window)

    window.select_region(1)
    _knobs(window, 1).widget("factor").setValue(4)
    window.select_region(0)
    _knobs(window, 1).widget("factor").setValue(8)
    driving.pump()

    # Two regions, two configurations. Addressed at the replicate the fan is
    # standing on, so the second edit pins the region it was made on and leaves
    # the first where its own edit put it — with the baseline as the address
    # both, the second value would be what every region resolved to.
    project = window.session.project
    assert project.params_for("n1", first)["factor"] == 8
    assert project.params_for("n1", second)["factor"] == 4


def test_a_knob_moves_the_baseline_where_the_project_has_no_regions(qapp, tmp_path: Path) -> None:
    del qapp
    path = _saved(tmp_path / "baseline.sieve.yaml", _project(("crop", "downsample", "detect"), ()))
    for window in _window(path):
        assert window.selected_replicate is None

        _knobs(window, 1).widget("factor").setValue(4)
        driving.pump()

        # The other arm of the one branch: an edit with no region to be about is
        # the node's own value, which is what such a project runs.
        assert window.session.project.pipeline.node("n1").params["factor"] == 4


@pytest.fixture
def placed_regions(stirred_clip: Path, tmp_path: Path) -> Path:
    """`crop -> downsample` over real footage, the two regions each placed.

    Placed rather than left to follow the baseline: two regions that deviate in
    nothing render the same picture whichever one a session is aimed at, so the
    override is what makes the two renders able to disagree.
    """
    video = tmp_path / stirred_clip.name
    video.write_bytes(stirred_clip.read_bytes())
    path = tmp_path / "arena.sieve.yaml"
    over(
        Project().model_copy(
            update={
                "pipeline": Pipeline(
                    nodes=(
                        Node(node_id="n0", tool_id="crop", version="1.0.0"),
                        Node(node_id="n1", tool_id="downsample", version="1.0.0"),
                    ),
                    edges=(Edge(upstream="n0", downstream="n1"),),
                ),
                "replicates": (
                    Replicate(name="north", overrides={"n0": {"region": _NORTH}}),
                    Replicate(name="south", overrides={"n0": {"region": _SOUTH}}),
                ),
            }
        ),
        video,
        tmp_path,
    ).save(path)
    return path


def test_the_loop_renders_the_region_the_fan_is_standing_on(qapp, placed_regions: Path) -> None:
    """A click onto a square moves the picture, not only the document.

    Taken through `TuningLoop.render_at`, which is what fills the viewport, and
    at a node *below* the crop, so what is asserted is that the whole tail of
    the graph follows the selection rather than that the crop node reports its
    own parameter back.

    Nothing sets the working window: the bar adopts the whole source when the
    container opens, and a stretch chosen on top of that would be a second thing
    this case waits for and no part of what it claims.
    """
    del qapp
    from sieve.gui.app import MainWindow
    from sieve.gui.project_select import projects_in

    window = MainWindow(projects_in(placed_regions.parent))
    try:
        window.open_project(placed_regions)
        driving.wait_until(lambda: window.tuning.is_open, _TIMEOUT_MS)
        # Anchored, as the window itself renders it: a source root's path is
        # stored relative to the project file, so a graph handed over as the
        # document spells it looks for the video beside this process.
        pipeline = anchored(window.session.project.pipeline, placed_regions.parent)

        north = window.tuning.render_at(pipeline, "n1", 0).result
        window.select_region(1)
        south = window.tuning.render_at(pipeline, "n1", 0).result

        assert window.tuning.last_error is None, window.tuning.last_error
        assert north is not None
        assert south is not None
        # Both boxes, not one and the whole frame: the second render is aimed by
        # the click, and the first by the aim the preview is opened with, so a
        # shape that survives says the opening path carries the selection too.
        assert north.shape == south.shape
        assert not np.array_equal(north, south)
    finally:
        window.close()


def test_a_step_reading_a_reshaped_frame_is_offered_no_regions(qapp, tmp_path: Path) -> None:
    del qapp
    path = _saved(
        tmp_path / "downstream.sieve.yaml",
        _project(
            ("downsample", "crop", "detect"),
            (Replicate(name="north"), Replicate(name="south")),
        ),
    )
    for window in _window(path):
        # The document has two regions and no card offers the verbs, because the
        # crop is handed a frame the window cannot name the size of: its box is
        # in the downsampled frame's pixels, the canvas has no editor for it
        # (`gui/kind_editors.RegionEditor`), and an override keyed there would be
        # a value in a space nothing in the window can convert out of.
        pane = window.control.pipeline_pane
        assert [card.regions for card in pane.cards] == [None, None, None]
        assert pane.fan is None
