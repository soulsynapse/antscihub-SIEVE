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
from sieve.core.pipeline_model import ClipRange, Edge, Node, Pipeline
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


def test_a_span_node_and_a_requested_clip_produce_the_same_frames(
    synthetic_video: Path,
) -> None:
    """The other half of the flip's equivalence, and the pushdown's whole claim.

    `docs/todo/the-graph-carries-the-crop-the-span-and-the-detector.md` will
    synthesize a span node from `Project.clip`, and it names the failure: a span
    node off by the lead-in the decode range absorbs. That mistake produces a run
    of exactly the right length over frames five earlier than the ones asked for,
    which reads as plausible everywhere except here.

    So the two paths are compared on the frames' *identities* rather than only on
    their count, and `background_ema` is in the chain because it is the thing a
    lead-in mistake actually corrupts — a stateful filter that saw five fewer
    frames of settling returns different pixels for the same index, and the
    lengths still match.
    """
    assert discover()
    graph = (
        Node(node_id="ema", filter_id="background_ema", version="1.0.0", params={}),
        Node(
            node_id="span",
            filter_id="span",
            version="1.0.0",
            params={"start": 22, "end": 26},
        ),
    )
    by_request = ExecutionPlan.build(
        Dag.build(Pipeline(nodes=graph[:1])),
        source=source_identity(synthetic_video),
        span=ClipRange(start=22, end=26),
        backend=Backend.CPU,
    )
    by_graph = ExecutionPlan.build(
        Dag.build(Pipeline(nodes=graph, edges=(Edge(upstream="ema", downstream="span"),))),
        source=source_identity(synthetic_video),
        # Deliberately wider than the node's range on both sides: the graph is
        # what narrows it, and a fold that ignored the node would run 10 frames.
        span=ClipRange(start=18, end=30),
        backend=Backend.CPU,
    )

    assert by_graph.span == by_request.span
    assert by_graph.decode_range == by_request.decode_range

    with VideoReader(synthetic_video, luma=by_request.luma) as reader:
        requested = [(r.index, r["ema"].data) for r in execute(by_request, reader)]
    with VideoReader(synthetic_video, luma=by_graph.luma) as reader:
        selected = [(r.index, r["span"].data) for r in execute(by_graph, reader)]

    assert [index for index, _ in selected] == [22, 23, 24, 25]
    assert all(
        left == right and np.array_equal(pixels, other)
        for (left, pixels), (right, other) in zip(requested, selected, strict=True)
    )


def test_a_crop_node_and_a_replicate_roi_produce_the_same_pixels(
    synthetic_video: Path,
) -> None:
    """The equivalence the schema flip rests on, established before it.

    `docs/todo/the-graph-carries-the-crop-the-span-and-the-detector.md` will
    synthesize a crop node from `Replicate.roi` and delete `plan.roi`, and its
    failure mode is a plausible frame — the right size, the wrong pixels, from a
    box read in a numbering nobody checked. This is that check while both paths
    still exist: the same region, once through `executor._crop` from the
    replicate and once through the filter at the root, frame for frame.

    Not a unit test against the kernel, because what could disagree is not the
    slice — it is where each path applies it and what it hands downstream.
    """
    assert discover()
    span = ClipRange(start=10, end=14)
    through_replicate = ExecutionPlan.build(
        Dag.build(
            Pipeline(
                nodes=(
                    Node(
                        node_id="down",
                        filter_id="downsample",
                        version="1.0.0",
                        params={"factor": FACTOR},
                    ),
                )
            )
        ),
        source=source_identity(synthetic_video),
        span=span,
        backend=Backend.CPU,
        replicate=Replicate(name="arena 1", roi=ARENA),
    )
    through_graph = ExecutionPlan.build(
        Dag.build(
            Pipeline(
                nodes=(
                    Node(
                        node_id="crop",
                        filter_id="crop",
                        version="1.0.0",
                        params={
                            "roi": {
                                "x": ARENA.x,
                                "y": ARENA.y,
                                "width": ARENA.width,
                                "height": ARENA.height,
                            }
                        },
                    ),
                    Node(
                        node_id="down",
                        filter_id="downsample",
                        version="1.0.0",
                        params={"factor": FACTOR},
                    ),
                ),
                edges=(Edge(upstream="crop", downstream="down"),),
            )
        ),
        source=source_identity(synthetic_video),
        span=span,
        backend=Backend.CPU,
        replicate=None,
    )

    with VideoReader(synthetic_video, luma=through_replicate.luma) as reader:
        cropped_by_plan = [result["down"].data for result in execute(through_replicate, reader)]
    with VideoReader(synthetic_video, luma=through_graph.luma) as reader:
        cropped_by_graph = [result["down"].data for result in execute(through_graph, reader)]

    assert len(cropped_by_plan) == 4
    assert all(
        np.array_equal(left, right)
        for left, right in zip(cropped_by_plan, cropped_by_graph, strict=True)
    )
    # And the pixels are the arena's rather than the whole frame's, which the
    # comparison above would be satisfied by if neither path cropped at all.
    assert cropped_by_graph[0].shape == (ARENA.height // FACTOR, ARENA.width // FACTOR)


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
