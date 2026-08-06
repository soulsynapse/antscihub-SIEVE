"""What a preview has to get right, and what each failure would look like.

Three claims, and none of them is about frames coming out — `test_executor.py`
and `test_executor_run.py` already own that. What is here is the arithmetic of
*re*-running, because a preview is the only caller that runs one graph over one
span again and again with one thing changed:

**An edit recomputes a suffix.** If it recomputes the graph, the 3 s budget is
met by the two-node fixture below and missed by a real chain, and nothing fails
in between — the frames are correct either way. The observable that separates
them is the reader: a re-render that decodes is a re-render that started over.

**Both budgets are published, nested, with the right one on a one-frame render.**
A preview whose numbers went nowhere would be the thing non-negotiable #4 calls
a budget that cannot be missed, and the keys are string literals in `preview.py`
because `sieve.bench` sits above `sieve.pipeline` — so the check that they name
real budgets has to happen from here, where both are importable.

**Moving the window keeps every entry.** A session that cleared its store would
be correct and would pay for the whole clip again to show a span the user had
already tuned.

A scratch registry and a hand-written kernel throughout: the claims are about
the session's bookkeeping, and a real filter would put its own arithmetic
between the assertion and the thing being asserted.
"""

from __future__ import annotations

from collections.abc import Generator, Iterator
from contextlib import contextmanager

import numpy as np
import pytest

from sieve.backend.dispatch import Backend, KernelRegistry, kernel
from sieve.bench.budgets import BUDGETS
from sieve.core.filter_base import ArraySpec, CostEstimate, ElementRelation, ParamsBase
from sieve.core.filter_registry import FilterRegistry, register_filter
from sieve.core.pipeline_model import ClipRange, Edge, Node, Pipeline
from sieve.core.types import ChannelSpec, Frame, WorkUnits
from sieve.pipeline.cache import MemoryFrameStore
from sieve.pipeline.preview import (
    FIRST_FRAME_BUDGET,
    WHOLE_WINDOW_BUDGET,
    PreviewSession,
)

SOURCE = "footage|1|2"
WIDTH, HEIGHT = 8, 6
WINDOW = ClipRange(start=10, end=14)


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


@pytest.fixture
def shelves() -> Iterator[tuple[FilterRegistry, KernelRegistry]]:
    """A one-filter world: adds `bias` to every pixel, and nothing else exists.

    Registered per test rather than at module scope so that two tests cannot
    reach each other's shelf, and so nothing here depends on what `discover()`
    happened to import.
    """
    filters = FilterRegistry()
    kernels = KernelRegistry()

    @register_filter(
        filter_id="bias",
        version="1.0.0",
        summary="Adds a constant to every pixel.",
        accepts=ArraySpec(),
        emits=ArraySpec(),
        element=ElementRelation.PRESERVED,
        cost=CostEstimate(work_per_megapixel=WorkUnits(1.0)),
        registry=filters,
    )
    class BiasParams(ParamsBase):
        bias: int = 0

    @kernel(BiasParams, Backend.CPU, registry=kernels)
    def bias_cpu(frame: Frame, params: BiasParams) -> Frame:
        return Frame(
            data=(frame.data + np.uint8(params.bias)),
            index=frame.index,
            channels=frame.channels,
        )

    assert callable(bias_cpu)
    yield filters, kernels


def chain(second_bias: int) -> Pipeline:
    """Two `bias` nodes in series, with the value of the *downstream* one free.

    Two nodes is the smallest graph in which "a suffix" and "the graph" are
    different things, which is the whole subject of the first test.
    """
    return Pipeline(
        nodes=(
            Node(node_id="head", filter_id="bias", version="1.0.0", params={"bias": 1}),
            Node(node_id="tail", filter_id="bias", version="1.0.0", params={"bias": second_bias}),
        ),
        edges=(Edge(upstream="head", downstream="tail"),),
    )


def session(
    shelves: tuple[FilterRegistry, KernelRegistry],
    reader: CountingSource,
    *,
    measure: RecordingMeasure | None = None,
    store: MemoryFrameStore | None = None,
) -> PreviewSession:
    filters, kernels = shelves
    return PreviewSession(
        source=SOURCE,
        reader=reader,
        window=WINDOW,
        measure=measure if measure is not None else RecordingMeasure(),
        store=MemoryFrameStore() if store is None else store,
        registry=filters,
        kernels=kernels,
    )


def test_an_edit_below_the_root_recomputes_the_suffix_and_decodes_nothing(
    shelves: tuple[FilterRegistry, KernelRegistry],
) -> None:
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
    preview = session(shelves, reader)

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


def test_the_first_frame_is_timed_inside_the_whole_render(
    shelves: tuple[FilterRegistry, KernelRegistry],
) -> None:
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
    preview = session(shelves, CountingSource(), measure=measure)

    preview.render_window(chain(2))

    assert measure.entered == [WHOLE_WINDOW_BUDGET, FIRST_FRAME_BUDGET]
    assert measure.closed == [FIRST_FRAME_BUDGET, WHOLE_WINDOW_BUDGET]

    preview.render_frame(chain(2), 11)

    assert measure.entered[2:] == [FIRST_FRAME_BUDGET]
    assert measure.closed[2:] == [FIRST_FRAME_BUDGET]

    # And both keys name budgets that exist. `preview.py` cannot make this
    # assertion — `sieve.bench` is above `sieve.pipeline` — so an unwatched
    # metric is caught here or on the first render against a real bus.
    assert {FIRST_FRAME_BUDGET, WHOLE_WINDOW_BUDGET} <= set(BUDGETS)


def test_moving_the_window_keeps_the_frames_the_two_spans_share(
    shelves: tuple[FilterRegistry, KernelRegistry],
) -> None:
    """A key carries no span, so a slid window pays only for the difference.

    Fails if `set_window` clears the store, which is the obvious implementation
    and would be invisible in the output: the frames are the same either way and
    the user waits for the whole clip again to look at a span they had already
    tuned.
    """
    reader = CountingSource()
    preview = session(shelves, reader)
    preview.render_window(chain(2))
    reader.reads.clear()

    preview.set_window(ClipRange(start=12, end=16))
    slid = preview.render_window(chain(2))

    assert slid.span == ClipRange(start=12, end=16)
    # Frames 12 and 13 are shared with the first window and were kept; 14 and 15
    # are new, and are the only ones the reader was asked for.
    assert (slid.computed, slid.from_cache) == (4, 4)
    assert reader.reads == [14, 15]
