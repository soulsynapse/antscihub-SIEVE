"""What a preview has to get right, and what each failure would look like.

Three claims, and none of them is about frames coming out — `test_executor.py`
already owns that. What is here is the arithmetic of *re*-running, because a
preview is the only caller that runs one graph over one span again and again
with one thing changed:

**An edit recomputes a suffix.** If it recomputes the graph, the 3 s budget is
met by the two-node fixture below and missed by a real chain, and nothing fails
in between — the frames are correct either way. The observable that separates
them is the reader: a re-render that decodes is a re-render that started over.

**Both budgets are published, nested, with the right one on a one-frame render.**
A preview whose numbers went nowhere would be a budget that cannot be missed,
and the keys are string literals in `preview.py` because `sieve.bench` sits
above `sieve.pipeline` — so the check that they name real budgets has to happen
from here, where both are importable.

**Moving the window keeps every entry.** A session that cleared its store would
be correct and would pay for the whole clip again to show a span the user had
already tuned.

**A source root is keyed, so the subtree under it is too.** A root whose file
the session never resolved is left out of the keys and takes everything below it
with it, so every render of such a graph recomputes the whole chain — correct
frames, no message, and the tuning loop gone.

v2's file holds these same **3 cases** and every one survives; what changes is
what a session is handed. The filter shelf and kernel shelf become one
`ToolRegistry` (`adr/no-kernel-apparatus.md`), `ClipRange` becomes `SourceSpan`,
and the `roi`/`backend` arguments are gone with the decisions that removed their
subjects — so the fixture is rewritten and the assertions are not.

A scratch shelf and a hand-written `run` throughout: the claims are about the
session's bookkeeping, and a real tool would put its own arithmetic between the
assertion and the thing being asserted.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from sieve.bench.budgets import BUDGETS
from sieve.core.pipeline_model import Edge, Node, Pipeline, SourceSpan
from sieve.core.tool_base import (
    SOURCE_ELEMENT_NAMES,
    ArraySpec,
    ElementKind,
    ElementRelation,
    Emission,
    ParamsBase,
    ParamStereotype,
)
from sieve.core.tool_registry import ToolRegistry, register_tool
from sieve.core.types import ChannelSpec, Frame, FrameIndex, FrameSpan
from sieve.pipeline.cache import MemoryFrameStore
from sieve.pipeline.preview import (
    FIRST_FRAME_BUDGET,
    WHOLE_WINDOW_BUDGET,
    PreviewSession,
)

SOURCE = "footage|1|2"
WIDTH, HEIGHT = 8, 6
WINDOW = SourceSpan(start=10, end=14)

#: A scratch shelf, not `REGISTRY` — `test_executor.py`'s reason: the
#: process-wide one is populated by tool modules at import, and registering into
#: it would make this file's behaviour depend on whether such an import had
#: already happened.
SHELF = ToolRegistry()


def bias_run(params: BiasParams, window: FrameSpan, state: None) -> Frame:
    del state
    frame = window.target
    return Frame(
        data=frame.data + np.uint8(params.bias),
        index=frame.index,
        channels=frame.channels,
    )


@register_tool(
    tool_id="bias",
    version="1.0.0",
    summary="Adds a constant to every pixel.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    run=bias_run,
    element=ElementRelation.PRESERVED,
    settling_epsilon=0.0,
    param_stereotypes={"bias": ParamStereotype.SCALAR_RANGE},
    registry=SHELF,
)
class BiasParams(ParamsBase):
    bias: int = 0


class ScratchPlate:
    """A `ToolSource`: the file a root reads, and the frames it hands back.

    Its pixels are the file's own size, so a swap of the file underneath a path
    that did not move is visible in the frames as well as in the keys — and the
    read is a `stat` rather than a decode, for the module docstring's reason.
    """

    def file(self, params: PlateParams, /) -> Path:
        return Path(params.path)

    def read(self, params: PlateParams, index: FrameIndex, /) -> Frame:
        return Frame(
            data=np.full((HEIGHT, WIDTH), Path(params.path).stat().st_size, dtype=np.uint8),
            index=FrameIndex.of(index),
            channels=ChannelSpec.GRAY,
        )


PLATE = ScratchPlate()


@register_tool(
    tool_id="plate",
    version="1.0.0",
    summary="Reads the file its own path parameter names.",
    accepts=ArraySpec(),
    emits=ArraySpec(dtypes=("uint8",), channels=(ChannelSpec.GRAY,)),
    emissions=(Emission("plate"),),
    source=PLATE,
    element=ElementKind.PIXEL,
    element_names=SOURCE_ELEMENT_NAMES,
    param_stereotypes={"path": ParamStereotype.PATH},
    registry=SHELF,
)
class PlateParams(ParamsBase):
    path: str = ""


class CountingSource:
    """Frame `n` is a flat field of intensity `n`, and every read is recorded.

    The read log is the observable the first test turns on: whether a re-render
    decoded is not visible in the frames it produced, and is exactly visible
    here.
    """

    def __init__(self) -> None:
        self.reads: list[int] = []

    def read(self, index: int) -> Frame:
        self.reads.append(index)
        return Frame(
            data=np.full((HEIGHT, WIDTH), min(index, 255), dtype=np.uint8),
            index=index,
            channels=ChannelSpec.GRAY,
        )


class RecordingMeasure:
    """A `Measure` that records what was timed and how it nested.

    `entered` is the order spans opened and `closed` the order they finished, so
    a nesting claim is two lists rather than a fake clock — the property being
    pinned is which span contains which, and a duration cannot state that.
    """

    def __init__(self) -> None:
        self.entered: list[str] = []
        self.closed: list[str] = []

    @contextmanager
    def __call__(self, key: str) -> Generator[None]:
        self.entered.append(key)
        yield
        self.closed.append(key)


def chain(second_bias: int) -> Pipeline:
    """Two `bias` nodes in series, with the value of the *downstream* one free.

    Two nodes is the smallest graph in which "a suffix" and "the graph" are
    different things, which is the whole subject of the first test.
    """
    return Pipeline(
        nodes=(
            Node(node_id="head", tool_id="bias", version="1.0.0", params={"bias": 1}),
            Node(node_id="tail", tool_id="bias", version="1.0.0", params={"bias": second_bias}),
        ),
        edges=(Edge(upstream="head", downstream="tail"),),
    )


def plated(directory: Path) -> Pipeline:
    """A source root and one node below it.

    Two nodes because that is where an unkeyed root costs more than itself: the
    node below folds its upstream's key in, so a root with none takes the whole
    chain under it out of the store.
    """
    return Pipeline(
        nodes=(
            Node(
                node_id="plate",
                tool_id="plate",
                version="1.0.0",
                params={"path": str(directory / "plate.raw")},
            ),
            Node(node_id="tail", tool_id="bias", version="1.0.0", params={"bias": 1}),
        ),
        edges=(Edge(upstream="plate", downstream="tail"),),
    )


def session(
    reader: CountingSource,
    *,
    measure: RecordingMeasure | None = None,
    store: MemoryFrameStore | None = None,
) -> PreviewSession:
    return PreviewSession(
        source=SOURCE,
        reader=reader,
        window=WINDOW,
        measure=measure if measure is not None else RecordingMeasure(),
        store=MemoryFrameStore() if store is None else store,
        registry=SHELF,
    )


def test_an_edit_below_the_root_recomputes_the_suffix_and_decodes_nothing() -> None:
    """The claim the module exists for, stated as a read count and two tallies.

    Editing `tail` leaves `head`'s keys untouched, so the second render serves
    four `head` outputs from the store and computes four `tail` outputs — and
    because every root hit, `execute` never asks the reader for a frame. A
    preview that re-ran from the source would produce identical frames, pass
    every other test in this repo, and turn a 3 s budget into a decode per edit.

    The third render is the other half: rendering the *same* graph again
    computes nothing at all, which is what says the tail's new keys were written
    rather than merely missed.
    """
    reader = CountingSource()
    preview = session(reader)

    first = preview.render_window(chain(2))
    assert first.frames == 4
    assert (first.computed, first.from_cache) == (8, 0)
    assert reader.reads == list(range(10, 14))

    reader.reads.clear()
    edited = preview.render_window(chain(3))

    assert edited.frames == 4
    assert (edited.computed, edited.from_cache) == (4, 4)
    assert edited.reuse == 0.5
    assert reader.reads == []

    unchanged = preview.render_window(chain(3))
    assert (unchanged.computed, unchanged.from_cache) == (0, 8)


def test_the_first_frame_is_timed_inside_the_whole_render() -> None:
    """Two spans for a window render, one for a frame render, nested correctly.

    The nesting is the load-bearing half. `slider_to_preview` answers "when did
    the user see something" and `full_preview_render` answers "when had they seen
    everything"; published side by side, the first would be charged the whole
    render and a preview that showed its first frame in 30 ms would report a
    100 ms budget miss.

    The one-frame render publishes only the first-frame key, because a cheap
    sample in the 3 s series would improve the median of the thing that measures
    a whole window.
    """
    measure = RecordingMeasure()
    preview = session(CountingSource(), measure=measure)

    preview.render_window(chain(2))

    assert measure.entered == [WHOLE_WINDOW_BUDGET, FIRST_FRAME_BUDGET]
    assert measure.closed == [FIRST_FRAME_BUDGET, WHOLE_WINDOW_BUDGET]

    rendered = preview.render_frame(chain(2), 11)

    assert rendered.span == SourceSpan(start=11, end=12)
    assert measure.entered[2:] == [FIRST_FRAME_BUDGET]
    assert measure.closed[2:] == [FIRST_FRAME_BUDGET]

    # And both keys name budgets that exist. `preview.py` cannot make this
    # assertion — `sieve.bench` is above `sieve.pipeline` — so an unwatched
    # metric is caught here or on the first render against a real bus.
    assert {FIRST_FRAME_BUDGET, WHOLE_WINDOW_BUDGET} <= set(BUDGETS)


def test_moving_the_window_keeps_the_frames_the_two_spans_share() -> None:
    """A key carries no span, so a slid window pays only for the difference.

    Fails if `set_window` clears the store, which is the obvious implementation
    and would be invisible in the output: the frames are the same either way and
    the user waits for the whole clip again to look at a span they had already
    tuned.
    """
    reader = CountingSource()
    preview = session(reader)
    preview.render_window(chain(2))
    reader.reads.clear()

    preview.set_window(SourceSpan(start=12, end=16))
    slid = preview.render_window(chain(2))

    assert slid.span == SourceSpan(start=12, end=16)
    # Frames 12 and 13 are shared with the first window and were kept; 14 and 15
    # are new, and are the only ones the reader was asked for.
    assert (slid.computed, slid.from_cache) == (4, 4)
    assert reader.reads == [14, 15]


def test_a_picked_source_root_is_keyed_and_so_is_the_chain_below_it(tmp_path: Path) -> None:
    """A session resolves its source roots, or its store answers nothing.

    `Dag.node_keys` skips a source root whose identity it was not given, and a
    node below an unkeyed one has no key either — so a session that never
    resolved the file renders this two-node graph from scratch every time, with
    the right frames and no message. The tallies are the observable: 8 computed
    twice rather than 8 then 0.

    The read log is the second half. Nothing here is fed by the footage, so a
    render that touched the reader would be one that had bound the picker to it.
    """
    (tmp_path / "plate.raw").write_bytes(b"a plate")
    reader = CountingSource()
    preview = session(reader)
    graph = plated(tmp_path)

    first = preview.render_window(graph)
    again = preview.render_window(graph)

    assert (first.computed, first.from_cache) == (8, 0)
    assert (again.computed, again.from_cache) == (0, 8)
    assert reader.reads == []
