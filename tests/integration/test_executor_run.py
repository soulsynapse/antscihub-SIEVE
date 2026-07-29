











from __future__ import annotations

from pathlib import Path

import numpy as np

from sieve.backend.dispatch import Backend
from sieve.core.pipeline_model import ClipRange, Node, Pipeline
from sieve.core.replicates import Replicate
from sieve.core.types import ROI, ChannelSpec, Frame
from sieve.decode.reader import VideoReader
from sieve.filters import discover
from sieve.filters.downsample import DownsampleParams, downsample_cpu
from sieve.pipeline.cache import MemoryFrameStore
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import execute
from sieve.pipeline.plan import ExecutionPlan




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
    assert discover()
    plan = ExecutionPlan.build(
        Dag.build(pipeline),
        source=source_identity(synthetic_video),
        span=ClipRange(start=10, end=14),
        backend=Backend.CPU,
        replicate=Replicate(name="arena 1", roi=ARENA),
    )



    assert plan.lead_in == 0

    store = MemoryFrameStore()
    with VideoReader(synthetic_video, luma=plan.luma) as reader:
        results = list(execute(plan, reader, store=store))

    assert [result.index for result in results] == [10, 11, 12, 13]
    assert all(
        result["down"].data.shape == (ARENA.height // FACTOR, ARENA.width // FACTOR)
        for result in results
    )






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










    assert len({result["down"].data.tobytes() for result in results}) >= 3



    assert len(store) == 4
    with VideoReader(synthetic_video, luma=plan.luma) as reader:
        again = list(execute(plan, reader, store=store))
    assert all(result.from_cache == frozenset({"down"}) for result in again)
