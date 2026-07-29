


























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
from sieve.core.types import ChannelSpec, Frame
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






    filters = FilterRegistry()
    kernels = KernelRegistry()

    @register_filter(
        filter_id="bias",
        version="1.0.0",
        summary="Adds a constant to every pixel.",
        accepts=ArraySpec(),
        emits=ArraySpec(),
        element=ElementRelation.PRESERVED,
        cost=CostEstimate(seconds_per_megapixel=0.001),
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












    measure = RecordingMeasure()
    preview = session(shelves, CountingSource(), measure=measure)

    preview.render_window(chain(2))

    assert measure.entered == [WHOLE_WINDOW_BUDGET, FIRST_FRAME_BUDGET]
    assert measure.closed == [FIRST_FRAME_BUDGET, WHOLE_WINDOW_BUDGET]

    preview.render_frame(chain(2), 11)

    assert measure.entered[2:] == [FIRST_FRAME_BUDGET]
    assert measure.closed[2:] == [FIRST_FRAME_BUDGET]




    assert {FIRST_FRAME_BUDGET, WHOLE_WINDOW_BUDGET} <= set(BUDGETS)


def test_moving_the_window_keeps_the_frames_the_two_spans_share(
    shelves: tuple[FilterRegistry, KernelRegistry],
) -> None:







    reader = CountingSource()
    preview = session(shelves, reader)
    preview.render_window(chain(2))
    reader.reads.clear()

    preview.set_window(ClipRange(start=12, end=16))
    slid = preview.render_window(chain(2))

    assert slid.span == ClipRange(start=12, end=16)


    assert (slid.computed, slid.from_cache) == (4, 4)
    assert reader.reads == [14, 15]
