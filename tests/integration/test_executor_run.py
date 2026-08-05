"""The whole path, with nothing faked: a file on disk to frames in hand.

Every other test of the executor substitutes something — a list for the
decoder, a scratch shelf for the registry, a hand-written kernel for a filter.
This one substitutes nothing, and so it is the only place that can catch the
seams between them: that `discover()` puts a spec and a kernel on the shelves
the plan and the executor actually read, that `source_identity` over a real
file produces a key the store round-trips, and that a real `VideoReader`
satisfies `FrameSource` — which is a structural claim no unit test asserting
against a fake can make.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from sieve.backend.dispatch import Backend
from sieve.core.pipeline_model import ClipRange, Node, Pipeline
from sieve.core.replicates import Replicate
from sieve.core.types import NO_FRAMES, ROI, ChannelSpec, Frame
from sieve.decode.reader import VideoReader
from sieve.filters import discover
from sieve.filters.downsample import DownsampleParams, downsample_cpu
from sieve.pipeline.cache import MemoryFrameStore
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import execute
from sieve.pipeline.plan import ExecutionPlan

#: A region of the 160x120 fixture, chosen so that halving it twice stays exact
#: — an odd extent would make the assertion about output shape a statement about
#: `//` rounding rather than about the graph.
ARENA = ROI(x=16, y=8, width=64, height=48)
FACTOR = 2


def test_a_real_video_through_a_real_filter(synthetic_video: Path) -> None:
    pipeline = Pipeline(
        nodes=(
            Node(
                node_id="down",
                filter_id="downsample",
                version="1.0.0",
                params={"factor": FACTOR},
            ),
        )
    )
    assert discover()  # the shelf the plan resolves against is the real one
    plan = ExecutionPlan.build(
        Dag.build(pipeline),
        source=source_identity(synthetic_video),
        span=ClipRange(start=10, end=14),
        backend=Backend.CPU,
        replicate=Replicate(name="arena 1", roi=ARENA),
    )
    # A stateless filter declares no warmup, so nothing is decoded ahead of the
    # span. Asserted rather than assumed: it is what makes the frame indices
    # below say what they say.
    assert plan.lead_in == NO_FRAMES

    store = MemoryFrameStore()
    with VideoReader(synthetic_video, luma=plan.luma) as reader:
        results = list(execute(plan, reader, store=store))

    assert [result.index for result in results] == [10, 11, 12, 13]
    assert all(
        result["down"].data.shape == (ARENA.height // FACTOR, ARENA.width // FACTOR)
        for result in results
    )
    # Byte for byte against the same three operations performed by hand. The
    # fixture's intensity ramp cannot serve here: `mp4v` is lossy and returns
    # ~46 where 50 was written, which is a larger error than the 5 that
    # separates adjacent frames — so a tolerance wide enough to accept the
    # codec is wide enough to accept the neighbouring frame, and the whole
    # point is to catch a crop taken from the neighbour.
    with VideoReader(synthetic_video, luma=plan.luma) as reader:
        expected = [
            downsample_cpu(
                Frame(
                    data=ARENA.crop(reader.read(index).data),
                    index=index,
                    channels=ChannelSpec.GRAY,
                ),
                DownsampleParams(factor=FACTOR),
            )
            for index in (10, 11, 12, 13)
        ]
    assert all(
        np.array_equal(result["down"].data, reference.data)
        for result, reference in zip(results, expected, strict=True)
    )
    # And they are not four copies of one frame, which the comparison above
    # would not notice if the reader had returned the same frame each time.
    #
    # Three rather than four, and it is the fixture rather than the executor:
    # `conftest`'s marker is the *blue* channel at `n * 5`, which BT.601 weights
    # at 0.114, so one frame of separation is ~0.6 luma levels — inside `mp4v`'s
    # own error. The fixture's "a test can assert which frame a seek landed on"
    # property holds on the colour path and does not survive the luma decode
    # this plan now keys for. Weakened here rather than papered over; a fixture
    # whose marker survives both formats is its own change.
    assert len({result["down"].data.tobytes() for result in results}) >= 3

    # And the entries are keyed such that a second run finds them, which needs
    # `source_identity`, `node_key`, and the store to agree about one string.
    assert len(store) == 4
    with VideoReader(synthetic_video, luma=plan.luma) as reader:
        again = list(execute(plan, reader, store=store))
    assert all(result.from_cache == frozenset({"down"}) for result in again)
