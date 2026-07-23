from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from antscihub_sieve.application.intensity import (
    ChannelStageOutcome,
    IntensityRequest,
    admit_result_memory,
    area_downsample,
    compute_intensity,
    reduce_rgb_frame,
)
from antscihub_sieve.application.resources import (
    DEFAULT_CPU_RESULT_MEMORY_BYTES,
    DEFAULT_GPU_RESULT_MEMORY_BYTES,
    ExecutionResourcePolicy,
)
from antscihub_sieve.application.working_grid import (
    WorkingGridSettings,
    resolve_working_grid,
)
from antscihub_sieve.application.working_window import (
    ExtentProvenance,
    FrameBatch,
    PlaneDescriptor,
    ResolvedWorkingWindow,
    WorkingWindowOutcome,
    WorkingWindowOutcomeKind,
    WorkingWindowRequest,
)
from antscihub_sieve.errors import SieveError


def plane(width: int, height: int) -> PlaneDescriptor:
    return PlaneDescriptor(
        plane_id="rgb24",
        width=width,
        height=height,
        channels=3,
        dtype="uint8",
        value_min=0,
        value_max=255,
        channel_order=("R", "G", "B"),
        backend="ffmpeg",
        source_pixel_format="yuv420p",
        source_color_range="tv",
        source_color_space="bt709",
        source_color_transfer="bt709",
        source_color_primaries="bt709",
    )


def request(
    *,
    width: int = 2,
    height: int = 2,
    start: int = 10,
    stop: int = 12,
    resources: ExecutionResourcePolicy = ExecutionResourcePolicy(),
) -> IntensityRequest:
    return IntensityRequest(
        working_window=WorkingWindowRequest(
            asset_ref=Path("asset.json"),
            expected_asset_id="asset-1",
            expected_content_sha256="abc",
            start_frame=start,
            stop_frame=stop,
        ),
        grid=resolve_working_grid(
            width,
            height,
            WorkingGridSettings.explicit(1),
        ),
        resources=resources,
    )


def resolved_for(item: IntensityRequest) -> ResolvedWorkingWindow:
    source = item.working_window
    return ResolvedWorkingWindow(
        sidecar_path=source.asset_ref,
        media_path=Path("video.mkv"),
        asset_id=source.expected_asset_id,
        content_sha256=source.expected_content_sha256,
        identity_status="verified",
        start_frame=source.start_frame,
        stop_frame=source.stop_frame,
        declared_stop=source.stop_frame,
        extent_provenance=ExtentProvenance.DECODED_COUNT,
        fps_num=30_000,
        fps_den=1_001,
        width=item.grid.source_width,
        height=item.grid.source_height,
        plane=plane(item.grid.source_width, item.grid.source_height),
    )


class FakeStream:
    def __init__(
        self,
        item: IntensityRequest,
        batches: list[FrameBatch],
        final_kind: WorkingWindowOutcomeKind = WorkingWindowOutcomeKind.COMPLETE,
    ) -> None:
        self.resolved = resolved_for(item)
        self._batches = batches
        self._final_kind = final_kind
        self.outcome: WorkingWindowOutcome | None = None
        self.closed = False

    def __iter__(self):  # type: ignore[no-untyped-def]
        for batch in self._batches:
            yield batch
        delivered = sum(len(batch.absolute_frame_indices) for batch in self._batches)
        self.outcome = WorkingWindowOutcome(
            kind=self._final_kind,
            requested_start=self.resolved.start_frame,
            requested_stop=self.resolved.stop_frame,
            delivered_start=self.resolved.start_frame,
            delivered_stop=self.resolved.start_frame + delivered,
            stopped_at_frame=None,
        )

    def close(self) -> None:
        self.closed = True
        if self.outcome is None:
            self.outcome = WorkingWindowOutcome(
                kind=WorkingWindowOutcomeKind.CANCELLED,
                requested_start=self.resolved.start_frame,
                requested_stop=self.resolved.stop_frame,
                delivered_start=self.resolved.start_frame,
                delivered_stop=self.resolved.start_frame,
                stopped_at_frame=self.resolved.start_frame,
            )


def test_intensity_contract_imports_without_qt() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import antscihub_sieve.application.intensity; "
                "assert not any(n == 'PyQt6' or n.startswith('PyQt6.') "
                "for n in sys.modules)"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_resource_defaults_are_explicit_cpu_and_gpu_budgets() -> None:
    assert DEFAULT_CPU_RESULT_MEMORY_BYTES == 16 * 1024**3
    assert DEFAULT_GPU_RESULT_MEMORY_BYTES == 6 * 1024**3


@pytest.mark.parametrize(
    ("rgb", "expected"),
    [
        ((0, 0, 0), 0.0),
        ((255, 255, 255), 1.0),
        ((255, 0, 0), 0.299),
        ((0, 255, 0), 0.587),
        ((0, 0, 255), 0.114),
    ],
)
def test_rgb601_primary_codes_are_fixed(
    rgb: tuple[int, int, int],
    expected: float,
) -> None:
    descriptor = plane(1, 1)
    grid = resolve_working_grid(
        1, 1, WorkingGridSettings.explicit(1)
    )
    result = reduce_rgb_frame(bytes(rgb), descriptor, grid)
    assert result.dtype == np.float32
    assert result.shape == (1, 1)
    assert float(result[0, 0]) == pytest.approx(expected, abs=1e-7)


def test_rgb_rule_is_not_bt709_or_limited_range() -> None:
    descriptor = plane(1, 1)
    grid = resolve_working_grid(1, 1)
    result = reduce_rgb_frame(bytes((255, 0, 0)), descriptor, grid)
    assert float(result[0, 0]) == pytest.approx(0.299, abs=1e-7)
    assert float(result[0, 0]) != pytest.approx(0.2126, abs=1e-3)
    assert float(result[0, 0]) != pytest.approx(
        (0.299 * 255 - 16) / 219,
        abs=1e-3,
    )


def test_area_downsample_uses_fractional_pixel_footprints() -> None:
    source = np.arange(15, dtype=np.float64).reshape(3, 5)
    resized = area_downsample(source, 2, 3)
    expected = np.empty((2, 3), dtype=np.float64)
    for target_y in range(2):
        y0, y1 = target_y * 3 / 2, (target_y + 1) * 3 / 2
        for target_x in range(3):
            x0, x1 = target_x * 5 / 3, (target_x + 1) * 5 / 3
            weighted_sum = 0.0
            for source_y in range(3):
                y_overlap = max(
                    0.0, min(y1, source_y + 1) - max(y0, source_y)
                )
                for source_x in range(5):
                    x_overlap = max(
                        0.0,
                        min(x1, source_x + 1) - max(x0, source_x),
                    )
                    weighted_sum += (
                        source[source_y, source_x]
                        * x_overlap
                        * y_overlap
                    )
            expected[target_y, target_x] = weighted_sum / (
                (x1 - x0) * (y1 - y0)
            )
    assert resized.dtype == np.float32
    assert resized == pytest.approx(expected, abs=1e-6)


def test_partial_cells_use_only_owned_working_pixels() -> None:
    descriptor = plane(3, 2)
    grid = resolve_working_grid(
        3, 2, WorkingGridSettings.explicit(2)
    )
    gray = bytes(
        component
        for value in (0, 0, 255, 255, 255, 0)
        for component in (value, value, value)
    )
    blocks = reduce_rgb_frame(gray, descriptor, grid)
    assert blocks.shape == (1, 2)
    assert blocks[0, 0] == pytest.approx(0.5)
    assert blocks[0, 1] == pytest.approx(0.5)
    assert grid.block_area_weight(0, 1) == 0.5


def test_malformed_frame_is_rejected_without_padding() -> None:
    with pytest.raises(SieveError, match="exact native-resolution"):
        reduce_rgb_frame(
            bytes(11),
            plane(2, 2),
            resolve_working_grid(2, 2),
        )


def test_memory_admission_happens_before_source_construction() -> None:
    over = request(
        start=0,
        stop=2,
        resources=ExecutionResourcePolicy(
            cpu_result_memory_bytes=31,
            gpu_result_memory_bytes=1,
        ),
    )
    opened = False

    def forbidden(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        nonlocal opened
        opened = True
        raise AssertionError("source should not open")

    with pytest.raises(SieveError) as raised:
        compute_intensity(over, stream_factory=forbidden)
    assert raised.value.code == "RESOURCE_RESULT_MEMORY_EXCEEDED"
    assert raised.value.context["requested_bytes"] == 32
    assert raised.value.context["allowed_bytes"] == 31
    assert not opened

    exact = request(
        start=0,
        stop=2,
        resources=ExecutionResourcePolicy(
            cpu_result_memory_bytes=32,
            gpu_result_memory_bytes=1,
        ),
    )
    assert admit_result_memory(exact) == 32


def test_cancellation_before_entry_opens_no_source() -> None:
    opened = False

    def forbidden(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        nonlocal opened
        opened = True
        raise AssertionError("source should not open")

    with pytest.raises(SieveError) as raised:
        compute_intensity(
            request(),
            cancelled=lambda: True,
            stream_factory=forbidden,
        )
    assert raised.value.code == "INTENSITY_CANCELLED"
    assert not opened


def test_complete_result_retains_provenance_and_is_immutable() -> None:
    item = request()
    descriptor = plane(2, 2)
    batches = [
        FrameBatch(
            absolute_frame_indices=(10, 11),
            frame_buffers=(
                bytes((255, 0, 0) * 4),
                bytes((0, 255, 0) * 4),
            ),
            plane=descriptor,
        )
    ]
    stream = FakeStream(item, batches)
    progress: list[tuple[int, int]] = []
    result = compute_intensity(
        item,
        progress=lambda done, total: progress.append((done, total)),
        stream_factory=lambda *_args, **_kwargs: stream,
    )
    assert stream.closed
    assert result.complete
    assert result.channel_outcome is ChannelStageOutcome.COMPLETED
    assert result.source_outcome.kind is WorkingWindowOutcomeKind.COMPLETE
    assert result.frame_indices == (10, 11)
    assert result.values.shape == (2, 2, 2)
    assert result.values[0] == pytest.approx(0.299)
    assert result.values[1] == pytest.approx(0.587)
    assert not result.values.flags.writeable
    assert result.plane.source_color_space == "bt709"
    assert result.conversion_id == "sieve.channel.rgb601_intensity.v1"
    assert result.backend.startswith("numpy-")
    assert progress == [(1, 2), (2, 2)]


def test_computation_failure_closes_stream_and_retains_processed_prefix() -> None:
    item = request()
    descriptor = plane(2, 2)
    stream = FakeStream(
        item,
        [
            FrameBatch(
                absolute_frame_indices=(10, 11),
                frame_buffers=(bytes((0, 0, 0) * 4), bytes(3)),
                plane=descriptor,
            )
        ],
    )
    result = compute_intensity(
        item,
        stream_factory=lambda *_args, **_kwargs: stream,
    )
    assert stream.closed
    assert not result.complete
    assert result.channel_outcome is ChannelStageOutcome.COMPUTATION_FAILED
    assert result.processed_start == 10
    assert result.processed_stop == 11
    assert result.values.shape == (1, 2, 2)
    assert result.error is not None


def test_source_failure_remains_distinct_from_channel_failure() -> None:
    item = request()

    class FailedSource(FakeStream):
        def __iter__(self):  # type: ignore[no-untyped-def]
            source_error = SieveError(
                "MEDIA_DECODE_FAILED",
                "Source decoder failed",
            )
            self.outcome = WorkingWindowOutcome(
                kind=WorkingWindowOutcomeKind.FAILED,
                requested_start=self.resolved.start_frame,
                requested_stop=self.resolved.stop_frame,
                delivered_start=self.resolved.start_frame,
                delivered_stop=self.resolved.start_frame,
                stopped_at_frame=self.resolved.start_frame,
                error=source_error,
            )
            raise source_error
            yield  # pragma: no cover

    stream = FailedSource(item, [])
    result = compute_intensity(
        item,
        stream_factory=lambda *_args, **_kwargs: stream,
    )
    assert stream.closed
    assert result.source_outcome.kind is WorkingWindowOutcomeKind.FAILED
    assert result.channel_outcome is ChannelStageOutcome.COMPLETED
    assert result.processed_start == result.processed_stop == 10
    assert result.error is result.source_outcome.error
