from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from antscihub_sieve.application.intensity import (
    ChannelStageOutcome,
    IntensityRequest,
    NormalizationMode,
    NormalizationSpec,
    admit_result_memory,
    area_downsample,
    compute_intensity,
    estimate_result_bytes,
    normalize_working_frame,
    process_rgb_frame,
    reduce_rgb_frame,
    reduce_working_frame,
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
    assert raised.value.context["requested_bytes"] == 34
    assert raised.value.context["allowed_bytes"] == 31
    assert not opened

    exact = request(
        start=0,
        stop=2,
        resources=ExecutionResourcePolicy(
            cpu_result_memory_bytes=34,
            gpu_result_memory_bytes=1,
        ),
    )
    assert admit_result_memory(exact) == 34


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
    assert result.degenerate_flags.tolist() == [0, 0]
    assert result.degenerate_flags.dtype == np.uint8
    assert result.degenerate_flags.nbytes == 2
    assert not result.degenerate_flags.flags.writeable
    assert result.plane.source_color_space == "bt709"
    assert result.conversion_id == "sieve.channel.rgb601_intensity.v1"
    assert result.normalization_id == "sieve.normalization.off.v1"
    assert result.scientific_units == "normalized RGB-code intensity fraction"
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


def test_off_normalization_is_an_exact_nonmutating_alias() -> None:
    frame = np.array(
        [[0.0, 0.25], [0.5, 1.0]],
        dtype=np.float32,
    )
    before = frame.copy()
    normalized, degenerate = normalize_working_frame(
        frame,
        NormalizationSpec.off(),
    )
    assert normalized is frame
    assert np.array_equal(normalized, before)
    assert not degenerate


def test_normalization_spec_pins_mode_defaults_and_rejects_bad_epsilon() -> None:
    direct = NormalizationSpec(
        mode=NormalizationMode.PER_FRAME_ZSCORE,
        epsilon=1e-6,
    )
    assert direct.implementation_id.endswith("population_zscore.v1")
    with pytest.raises(ValueError, match="does not accept epsilon"):
        NormalizationSpec(
            mode=NormalizationMode.OFF,
            epsilon=1e-6,
        )
    with pytest.raises(ValueError, match="finite and positive"):
        NormalizationSpec.per_frame_zscore(epsilon=float("nan"))


def test_population_zscore_matches_hand_computed_reference() -> None:
    frame = np.array([[0.0, 1.0], [2.0, 3.0]], dtype=np.float32)
    before = frame.copy()
    normalized, degenerate = normalize_working_frame(
        frame,
        NormalizationSpec.per_frame_zscore(),
    )
    expected = np.array(
        [
            [-1.3416408, -0.4472136],
            [0.4472136, 1.3416408],
        ],
        dtype=np.float32,
    )
    assert not degenerate
    assert normalized.dtype == np.float32
    assert normalized == pytest.approx(expected, abs=1e-7)
    assert float(np.mean(normalized, dtype=np.float64)) == pytest.approx(
        0.0,
        abs=1e-7,
    )
    assert float(np.std(normalized, dtype=np.float64, ddof=0)) == pytest.approx(
        1.0,
        abs=1e-7,
    )
    assert float(np.std(normalized, dtype=np.float64, ddof=1)) != pytest.approx(
        1.0,
        abs=1e-3,
    )
    assert np.array_equal(frame, before)


@pytest.mark.parametrize(
    "frame",
    [
        np.full((2, 2), 0.25, dtype=np.float32),
        np.zeros((2, 2), dtype=np.float32),
        np.array([[0.75]], dtype=np.float32),
    ],
)
def test_degenerate_zscore_is_exact_zero(frame: np.ndarray) -> None:
    normalized, degenerate = normalize_working_frame(
        frame,
        NormalizationSpec.per_frame_zscore(),
    )
    assert degenerate
    assert normalized.dtype == np.float32
    assert np.array_equal(normalized, np.zeros_like(frame))


def test_zscore_epsilon_boundary_uses_strict_less_than() -> None:
    frame = np.array([[-1e-6, 1e-6]], dtype=np.float32)
    sigma = float(np.std(frame.astype(np.float64), ddof=0))
    at_boundary, boundary_degenerate = normalize_working_frame(
        frame,
        NormalizationSpec.per_frame_zscore(epsilon=sigma),
    )
    below_boundary, below_degenerate = normalize_working_frame(
        frame,
        NormalizationSpec.per_frame_zscore(epsilon=sigma * 1.01),
    )
    assert not boundary_degenerate
    assert at_boundary == pytest.approx(
        np.array([[-1.0, 1.0]], dtype=np.float32)
    )
    assert below_degenerate
    assert np.array_equal(below_boundary, np.zeros_like(frame))


def test_zscore_is_positive_affine_invariant_and_unclipped() -> None:
    frame = np.array([[0.0, 1.0], [2.0, 20.0]], dtype=np.float32)
    transformed = frame * np.float32(3.5) + np.float32(7.0)
    first, _ = normalize_working_frame(
        frame,
        NormalizationSpec.per_frame_zscore(),
    )
    second, _ = normalize_working_frame(
        transformed,
        NormalizationSpec.per_frame_zscore(),
    )
    assert first == pytest.approx(second, abs=2e-7)
    assert float(np.max(first)) > 1.0
    assert float(np.min(first)) < 0.0


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_zscore_rejects_any_nonfinite_input(value: float) -> None:
    frame = np.array([[0.0, value]], dtype=np.float32)
    with pytest.raises(SieveError) as raised:
        normalize_working_frame(
            frame,
            NormalizationSpec.per_frame_zscore(),
        )
    assert raised.value.code == "NORMALIZATION_NONFINITE"
    assert raised.value.context["stage"] == "normalization"


def test_required_order_is_downsample_then_normalize_then_block() -> None:
    native = np.array([[0.0, 0.0, 0.0, 1.0]], dtype=np.float32)
    working = area_downsample(native, 1, 2)
    selected, _ = normalize_working_frame(
        working,
        NormalizationSpec.per_frame_zscore(),
    )
    native_z, _ = normalize_working_frame(
        native,
        NormalizationSpec.per_frame_zscore(),
    )
    wrong_downsample_order = area_downsample(native_z, 1, 2)
    assert selected == pytest.approx(
        np.array([[-1.0, 1.0]], dtype=np.float32)
    )
    assert not np.allclose(selected, wrong_downsample_order)

    grid = resolve_working_grid(4, 1, WorkingGridSettings.explicit(2))
    selected_blocks = reduce_working_frame(
        normalize_working_frame(
            native,
            NormalizationSpec.per_frame_zscore(),
        )[0],
        grid,
    )
    block_first = reduce_working_frame(native, grid)
    wrong_block_order, _ = normalize_working_frame(
        block_first,
        NormalizationSpec.per_frame_zscore(),
    )
    assert not np.allclose(selected_blocks, wrong_block_order)


def test_partial_cells_are_included_once_and_reconstruct_zero_mean() -> None:
    grid = resolve_working_grid(3, 2, WorkingGridSettings.explicit(2))
    frame = np.arange(6, dtype=np.float32).reshape(2, 3)
    normalized, _ = normalize_working_frame(
        frame,
        NormalizationSpec.per_frame_zscore(),
    )
    blocks = reduce_working_frame(normalized, grid)
    owned_areas = np.array(
        [
            grid.block_area(row, column)
            for row in range(grid.rows)
            for column in range(grid.columns)
        ],
        dtype=np.float64,
    )
    weighted = np.average(blocks.ravel(), weights=owned_areas)
    assert weighted == pytest.approx(0.0, abs=1e-7)


def test_scientific_key_tracks_normalization_not_execution_policy() -> None:
    off = request()
    zscore = IntensityRequest(
        working_window=off.working_window,
        grid=off.grid,
        normalization=NormalizationSpec.per_frame_zscore(),
        resources=ExecutionResourcePolicy(
            cpu_result_memory_bytes=99,
            gpu_result_memory_bytes=1,
        ),
        batch_size=7,
    )
    same_science = IntensityRequest(
        working_window=off.working_window,
        grid=off.grid,
        resources=ExecutionResourcePolicy(
            cpu_result_memory_bytes=99,
            gpu_result_memory_bytes=1,
        ),
        batch_size=7,
    )
    changed_epsilon = IntensityRequest(
        working_window=off.working_window,
        grid=off.grid,
        normalization=NormalizationSpec.per_frame_zscore(epsilon=2e-6),
    )
    changed_implementation = IntensityRequest(
        working_window=off.working_window,
        grid=off.grid,
        normalization=NormalizationSpec.per_frame_zscore(
            implementation_id="test.normalization.v2",
        ),
    )
    assert off.scientific_key == same_science.scientific_key
    assert off.scientific_key != zscore.scientific_key
    assert zscore.scientific_key != changed_epsilon.scientific_key
    assert zscore.scientific_key != changed_implementation.scientific_key


def test_zscore_result_retains_flags_units_and_composite_bytes() -> None:
    item = request(start=0, stop=1)
    item = IntensityRequest(
        working_window=item.working_window,
        grid=item.grid,
        normalization=NormalizationSpec.per_frame_zscore(),
    )
    descriptor = plane(2, 2)
    stream = FakeStream(
        item,
        [
            FrameBatch(
                absolute_frame_indices=(0,),
                frame_buffers=(bytes((128, 128, 128) * 4),),
                plane=descriptor,
            )
        ],
    )
    result = compute_intensity(
        item,
        stream_factory=lambda *_args, **_kwargs: stream,
    )
    assert result.complete
    assert np.array_equal(result.values, np.zeros((1, 2, 2), np.float32))
    assert result.degenerate_flags.tolist() == [1]
    assert result.degenerate_flags.nbytes == 1
    assert result.scientific_units == "frame population standard deviations"
    assert result.normalization_id.endswith("population_zscore.v1")
    assert estimate_result_bytes(item) == 17


def test_process_rgb_frame_applies_normalization_before_blocks() -> None:
    descriptor = plane(2, 2)
    grid = resolve_working_grid(2, 2, WorkingGridSettings.explicit(1))
    raw = bytes(
        component
        for value in (0, 64, 128, 255)
        for component in (value, value, value)
    )
    blocks, degenerate = process_rgb_frame(
        raw,
        descriptor,
        grid,
        NormalizationSpec.per_frame_zscore(),
    )
    assert not degenerate
    assert float(np.mean(blocks, dtype=np.float64)) == pytest.approx(
        0.0,
        abs=1e-7,
    )
    assert float(np.std(blocks, dtype=np.float64)) == pytest.approx(
        1.0,
        abs=1e-7,
    )


def test_batch_size_does_not_change_normalized_results() -> None:
    base = request(start=0, stop=2)
    descriptor = plane(2, 2)
    frames = (
        bytes(
            component
            for value in (0, 32, 128, 255)
            for component in (value, value, value)
        ),
        bytes(
            component
            for value in (255, 160, 64, 0)
            for component in (value, value, value)
        ),
    )

    def compute(batch_size: int, batches: list[FrameBatch]):
        item = IntensityRequest(
            working_window=base.working_window,
            grid=base.grid,
            normalization=NormalizationSpec.per_frame_zscore(),
            batch_size=batch_size,
        )
        stream = FakeStream(item, batches)
        return compute_intensity(
            item,
            stream_factory=lambda *_args, **_kwargs: stream,
        )

    separate = compute(
        1,
        [
            FrameBatch((0,), (frames[0],), descriptor),
            FrameBatch((1,), (frames[1],), descriptor),
        ],
    )
    combined = compute(
        2,
        [FrameBatch((0, 1), frames, descriptor)],
    )
    assert np.array_equal(separate.values, combined.values)
    assert np.array_equal(
        separate.degenerate_flags,
        combined.degenerate_flags,
    )
    assert separate.scientific_key == combined.scientific_key


def test_overlapping_frame_is_window_independent() -> None:
    descriptor = plane(2, 2)
    common = bytes(
        component
        for value in (0, 64, 128, 255)
        for component in (value, value, value)
    )

    def compute(start: int, frames: tuple[bytes, bytes]):
        item = request(start=start, stop=start + 2)
        item = IntensityRequest(
            working_window=item.working_window,
            grid=item.grid,
            normalization=NormalizationSpec.per_frame_zscore(),
        )
        stream = FakeStream(
            item,
            [
                FrameBatch(
                    (start, start + 1),
                    frames,
                    descriptor,
                )
            ],
        )
        return compute_intensity(
            item,
            stream_factory=lambda *_args, **_kwargs: stream,
        )

    first = compute(0, (bytes((0, 0, 0) * 4), common))
    second = compute(1, (common, bytes((255, 255, 255) * 4)))
    assert np.array_equal(first.values[1], second.values[0])
    assert first.degenerate_flags[1] == second.degenerate_flags[0]
