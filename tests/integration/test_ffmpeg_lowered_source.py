"""The FFmpeg-lowered source route is a source contract, not a hidden shortcut."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from sieve.backend.dispatch import Backend
from sieve.core.pipeline_model import ClipRange, Edge, Node, Pipeline
from sieve.core.replicates import Replicate
from sieve.core.types import ROI, FrameIndex, VideoMetadata
from sieve.decode.ffmpeg import (
    FfmpegLoweredFrameSource,
    ffmpeg_decoder_identity,
    ffmpeg_lowered_command,
)
from sieve.decode.lowered import LoweredPrefix, LoweredScale, LoweredStep
from sieve.decode.reader import VideoDecodeError, VideoReader
from sieve.filters import discover
from sieve.pipeline.cache import MemoryFrameStore
from sieve.pipeline.cache_key import source_identity, source_key
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import execute
from sieve.pipeline.lowering import lower_resolved_source, lower_root_prefix
from sieve.pipeline.plan import ExecutionPlan
from sieve.pipeline.resolve_source import ResolvedSource

SOURCE_ROI = ROI(x=17, y=9, width=65, height=49)


def _metadata(path: Path = Path("source.mp4")) -> VideoMetadata:
    return VideoMetadata(path=path, width=160, height=120, fps=Fraction(20), frame_count=40)


def _chain(*nodes: Node) -> Pipeline:
    return Pipeline(
        nodes=nodes,
        edges=tuple(
            Edge(upstream=nodes[index].node_id, downstream=nodes[index + 1].node_id)
            for index in range(len(nodes) - 1)
        ),
    )


def _prefix(roi: ROI = SOURCE_ROI) -> LoweredPrefix:
    return LoweredPrefix(
        decoder_identity="ffmpeg-test",
        source_roi=roi,
        ffmpeg_roi=roi,
        scale=LoweredScale(
            filter_id="downsample",
            version="1.0.0",
            params_json='{"anti_alias":true,"factor":2}',
            output_width=roi.width // 2,
            output_height=roi.height // 2,
        ),
        steps=(
            LoweredStep("source-roi", "1", '{"height":49,"width":65,"x":17,"y":9}'),
            LoweredStep("downsample", "1.0.0", '{"anti_alias":true,"factor":2}'),
        ),
    )


def test_the_lowered_route_and_prefix_separate_source_keys() -> None:
    prefix = _prefix()

    assert source_key("footage", roi=SOURCE_ROI, luma=True) != source_key(
        "footage", luma=True, lowered_prefix=prefix
    )
    assert source_key("footage", luma=True, lowered_prefix=prefix) != source_key(
        "footage", luma=True, lowered_prefix=_prefix(ROI(x=19, y=9, width=65, height=49))
    )
    assert prefix.cache_parts()["route"] == "ffmpeg-lowered-gray8"
    assert prefix.cache_parts()["crop_exact"] is True
    with pytest.raises(ValueError, match="carries its crop"):
        source_key("footage", roi=SOURCE_ROI, luma=True, lowered_prefix=prefix)
    with pytest.raises(ValueError, match="emits gray"):
        source_key("footage", luma=False, lowered_prefix=prefix)


def test_an_odd_origin_source_roi_lowers_with_ffmpeg_exact_crop() -> None:
    discover()
    dag = Dag.build(
        _chain(
            Node(
                node_id="small",
                filter_id="downsample",
                version="1.0.0",
                params={"factor": 2},
            ),
            Node(node_id="norm", filter_id="normalize", version="1.0.0", params={}),
        )
    )
    replicate = Replicate(replicate_id="a", name="arena 1", roi=SOURCE_ROI)

    lowered = lower_root_prefix(
        dag,
        replicate=replicate,
        source_metadata=_metadata(),
        decoder_identity="ffmpeg-test",
    )

    assert lowered is not None
    assert lowered.removed == ("small",)
    assert [node.node_id for node in lowered.dag.order] == ["norm"]
    assert lowered.prefix.filtergraph == (
        "crop=65:49:17:9:exact=1,scale=32:24:flags=area,format=gray"
    )
    command = ffmpeg_lowered_command(
        Path("source.mp4"),
        lowered.prefix,
        start_index=10,
        fps=Fraction(20),
        workers=3,
    )
    assert command[command.index("-threads") + 1] == "3"
    assert command[command.index("-filter_threads") + 1] == "3"
    assert command[command.index("-filter_complex_threads") + 1] == "3"
    assert command[command.index("-vf") + 1] == lowered.prefix.filtergraph
    assert command[command.index("-pix_fmt") + 1] == "gray"


def test_only_root_side_source_space_work_is_lowered() -> None:
    discover()
    no_source_crop = Dag.build(
        _chain(
            Node(
                node_id="small",
                filter_id="downsample",
                version="1.0.0",
                params={"factor": 2},
            ),
            Node(
                node_id="post_crop",
                filter_id="crop",
                version="1.0.0",
                params={"roi": {"x": 1, "y": 1, "width": 8, "height": 8}},
            ),
        )
    )
    assert (
        lower_root_prefix(
            no_source_crop,
            replicate=None,
            source_metadata=_metadata(),
            decoder_identity="ffmpeg-test",
        )
        is None
    )

    source_crop = Dag.build(
        _chain(
            Node(
                node_id="crop",
                filter_id="crop",
                version="1.0.0",
                params={
                    "roi": {
                        "x": SOURCE_ROI.x,
                        "y": SOURCE_ROI.y,
                        "width": SOURCE_ROI.width,
                        "height": SOURCE_ROI.height,
                    }
                },
            ),
            Node(
                node_id="small",
                filter_id="downsample",
                version="1.0.0",
                params={"factor": 2},
            ),
            Node(node_id="norm", filter_id="normalize", version="1.0.0", params={}),
        )
    )
    lowered = lower_root_prefix(
        source_crop,
        replicate=None,
        source_metadata=_metadata(),
        decoder_identity="ffmpeg-test",
    )
    assert lowered is not None
    assert lowered.removed == ("crop", "small")

    protected = lower_root_prefix(
        source_crop,
        replicate=None,
        source_metadata=_metadata(),
        decoder_identity="ffmpeg-test",
        protected_nodes=("small",),
    )
    assert protected is None


def test_the_executor_receives_working_size_gray_frames_from_ffmpeg(
    synthetic_video: Path,
) -> None:
    try:
        decoder = ffmpeg_decoder_identity()
    except VideoDecodeError as error:
        pytest.skip(f"FFmpeg is not available: {error}")

    discover()
    pipeline = _chain(
        Node(
            node_id="small",
            filter_id="downsample",
            version="1.0.0",
            params={"factor": 2},
        ),
        Node(node_id="norm", filter_id="normalize", version="1.0.0", params={}),
    )
    dag = Dag.build(pipeline)
    replicate = Replicate(replicate_id="a", name="arena 1", roi=SOURCE_ROI)
    with VideoReader(synthetic_video, luma=True) as reader:
        metadata = reader.metadata
    dag, resolved = lower_resolved_source(
        dag,
        ResolvedSource(
            path=synthetic_video,
            identity=source_identity(synthetic_video),
            pre_cropped=False,
            first_index=FrameIndex(0),
        ),
        replicate=replicate,
        source_metadata=metadata,
        decoder_identity=decoder,
    )
    assert resolved.lowered_prefix is not None
    plan = ExecutionPlan.build(
        dag,
        source=resolved.identity,
        span=ClipRange(start=10, end=14),
        backend=Backend.CPU,
        replicate=replicate,
        pre_cropped=resolved.pre_cropped,
        source_start=resolved.first_index,
        lowered_prefix=resolved.lowered_prefix,
    )

    with FfmpegLoweredFrameSource(
        synthetic_video,
        resolved.lowered_prefix,
        workers=1,
        source_metadata=metadata,
    ) as reader:
        results = list(execute(plan, resolved.wrap(reader), store=MemoryFrameStore()))

    assert [node.node_id for node in plan.dag.order] == ["norm"]
    assert [result.index for result in results] == [10, 11, 12, 13]
    assert all(result.source is not None for result in results)
    assert all(result.source_cropped for result in results)
    assert all(
        result.source.data.shape == (SOURCE_ROI.height // 2, SOURCE_ROI.width // 2)
        for result in results
        if result.source is not None
    )
