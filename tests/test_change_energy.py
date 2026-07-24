from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from antscihub_sieve.application.change_energy import (
    ChangeEnergyRequest,
    admit_result_memory,
    change_energy_pair,
    compute_change_energy,
    estimate_result_bytes,
    gaussian_integrate,
    gaussian_kernel,
)
from antscihub_sieve.application.intensity import NormalizationSpec
from antscihub_sieve.application.resources import ExecutionResourcePolicy
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
        backend="fixture",
        source_pixel_format="rgb24",
        source_color_range="full",
        source_color_space=None,
        source_color_transfer=None,
        source_color_primaries=None,
    )


def request(
    start: int = 1,
    stop: int = 4,
    *,
    width: int = 3,
    height: int = 2,
    normalization: NormalizationSpec = NormalizationSpec(),
    block_size: int = 2,
) -> ChangeEnergyRequest:
    return ChangeEnergyRequest(
        working_window=WorkingWindowRequest(
            asset_ref=Path("asset.sieve.json"),
            expected_asset_id="asset",
            expected_content_sha256="sha",
            start_frame=start,
            stop_frame=stop,
        ),
        grid=resolve_working_grid(
            width,
            height,
            WorkingGridSettings.explicit(block_size),
        ),
        normalization=normalization,
    )


class FakeStream:
    def __init__(
        self,
        source_request: WorkingWindowRequest,
        item: ChangeEnergyRequest,
        frames: list[bytes],
        *,
        batch_size: int = 1,
    ) -> None:
        descriptor = plane(item.grid.source_width, item.grid.source_height)
        self.resolved = ResolvedWorkingWindow(
            sidecar_path=Path("asset.sieve.json"),
            media_path=Path("asset.mkv"),
            asset_id="asset",
            content_sha256="sha",
            identity_status="recorded",
            start_frame=source_request.start_frame,
            stop_frame=source_request.stop_frame,
            declared_stop=100,
            extent_provenance=ExtentProvenance.DECODED_COUNT,
            fps_num=30,
            fps_den=1,
            width=descriptor.width,
            height=descriptor.height,
            plane=descriptor,
        )
        indices = list(range(source_request.start_frame, source_request.stop_frame))
        self._batches = [
            FrameBatch(
                absolute_frame_indices=tuple(indices[offset : offset + batch_size]),
                frame_buffers=tuple(frames[offset : offset + batch_size]),
                plane=descriptor,
            )
            for offset in range(0, len(indices), batch_size)
        ]
        self.outcome: WorkingWindowOutcome | None = None
        self.closed = False

    def __iter__(self):  # type: ignore[no-untyped-def]
        yield from self._batches
        self.outcome = WorkingWindowOutcome(
            kind=WorkingWindowOutcomeKind.COMPLETE,
            requested_start=self.resolved.start_frame,
            requested_stop=self.resolved.stop_frame,
            delivered_start=self.resolved.start_frame,
            delivered_stop=self.resolved.stop_frame,
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


def rgb_frame(width: int, height: int, value: int) -> bytes:
    return np.full((height, width, 3), value, dtype=np.uint8).tobytes()


def test_contract_imports_without_qt() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import antscihub_sieve.application.change_energy; "
                "assert not any(n == 'PyQt6' or n.startswith('PyQt6.') "
                "for n in sys.modules)"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_fixed_gaussian_matches_direct_reflect101_reference() -> None:
    field = np.arange(15, dtype=np.float32).reshape(3, 5) ** 2
    kernel = gaussian_kernel()
    expected = np.empty_like(field)
    for y in range(field.shape[0]):
        for x in range(field.shape[1]):
            total = 0.0
            for ky, wy in enumerate(kernel):
                sy = _reflect101(y + ky - 8, field.shape[0])
                for kx, wx in enumerate(kernel):
                    sx = _reflect101(x + kx - 8, field.shape[1])
                    total += float(field[sy, sx]) * wy * wx
            expected[y, x] = total
    assert np.allclose(gaussian_integrate(field), expected, rtol=1e-6, atol=1e-6)


def _reflect101(index: int, size: int) -> int:
    if size == 1:
        return 0
    while index < 0 or index >= size:
        index = -index if index < 0 else 2 * size - 2 - index
    return index


def test_pair_is_current_minus_previous_squared_then_integrated_and_reduced() -> None:
    grid = resolve_working_grid(2, 2, WorkingGridSettings.explicit(1))
    previous = np.zeros((2, 2), dtype=np.float32)
    current = np.array([[0.0, 1.0], [2.0, 3.0]], dtype=np.float32)
    expected = gaussian_integrate(current * current)
    actual = change_energy_pair(previous, current, grid)
    assert np.allclose(actual, expected, rtol=1e-6, atol=1e-6)
    assert actual.dtype == np.float32


def test_mid_window_reads_one_context_frame_and_aligns_to_later_frames() -> None:
    item = request(17, 20, width=2, height=1, block_size=1)
    frames = [rgb_frame(2, 1, value) for value in (0, 32, 64, 96)]
    captured: list[WorkingWindowRequest] = []
    streams: list[FakeStream] = []

    def factory(source_request, *, batch_size, cancelled):  # type: ignore[no-untyped-def]
        captured.append(source_request)
        stream = FakeStream(source_request, item, frames, batch_size=batch_size)
        streams.append(stream)
        return stream

    result = compute_change_energy(item, stream_factory=factory)
    assert (captured[0].start_frame, captured[0].stop_frame) == (16, 20)
    assert result.complete
    assert result.processed_start == 17
    assert result.processed_stop == 20
    assert result.valid_start == 17
    assert result.valid_stop == 20
    assert result.temporal_valid.tolist() == [1, 1, 1]
    assert np.all(result.values > 0)
    assert streams[0].closed


def test_frame_zero_is_explicitly_invalid_and_never_counted_as_zero_energy() -> None:
    item = request(0, 3, width=1, height=1, block_size=1)
    frames = [rgb_frame(1, 1, value) for value in (0, 64, 128)]

    def factory(source_request, *, batch_size, cancelled):  # type: ignore[no-untyped-def]
        return FakeStream(source_request, item, frames, batch_size=batch_size)

    result = compute_change_energy(item, stream_factory=factory)
    assert result.complete
    assert result.temporal_valid.tolist() == [0, 1, 1]
    assert result.previous_degenerate.tolist() == [-1, 0, 0]
    assert result.values[0].tolist() == [[0.0]]
    assert result.valid_start == 1


def test_zscore_degenerate_evidence_is_retained_per_pair() -> None:
    item = request(
        1,
        3,
        width=2,
        height=1,
        normalization=NormalizationSpec.per_frame_zscore(),
        block_size=1,
    )
    frames = [
        rgb_frame(2, 1, 20),
        np.array([[[0, 0, 0], [255, 255, 255]]], dtype=np.uint8).tobytes(),
        rgb_frame(2, 1, 40),
    ]

    def factory(source_request, *, batch_size, cancelled):  # type: ignore[no-untyped-def]
        return FakeStream(source_request, item, frames, batch_size=batch_size)

    result = compute_change_energy(item, stream_factory=factory)
    assert result.previous_degenerate.tolist() == [1, 0]
    assert result.current_degenerate.tolist() == [0, 1]
    assert result.temporal_valid.tolist() == [1, 1]
    assert result.scientific_units == "z-score squared"


def test_admission_accounts_for_all_retained_arrays_before_source() -> None:
    item = request(1, 4, width=3, height=2, block_size=2)
    expected = 3 * 1 * 2 * 4 + 3 * 3
    assert estimate_result_bytes(item) == expected
    exact = ChangeEnergyRequest(
        working_window=item.working_window,
        grid=item.grid,
        resources=ExecutionResourcePolicy(
            cpu_result_memory_bytes=expected,
            gpu_result_memory_bytes=1,
        ),
    )
    assert admit_result_memory(exact) == expected
    rejected = ChangeEnergyRequest(
        working_window=item.working_window,
        grid=item.grid,
        resources=ExecutionResourcePolicy(
            cpu_result_memory_bytes=expected - 1,
            gpu_result_memory_bytes=1,
        ),
    )
    with pytest.raises(SieveError, match="configured result-memory budget"):
        compute_change_energy(
            rejected,
            stream_factory=lambda *_args, **_kwargs: pytest.fail(
                "source must not open"
            ),
        )


def test_batch_size_does_not_change_result() -> None:
    base = request(1, 4, width=2, height=1, block_size=1)
    frames = [rgb_frame(2, 1, value) for value in (0, 32, 96, 128)]

    def run(batch_size: int):
        item = ChangeEnergyRequest(
            working_window=base.working_window,
            grid=base.grid,
            batch_size=batch_size,
        )

        def factory(source_request, *, batch_size, cancelled):  # type: ignore[no-untyped-def]
            return FakeStream(source_request, item, frames, batch_size=batch_size)

        return compute_change_energy(item, stream_factory=factory)

    one = run(1)
    three = run(3)
    assert np.array_equal(one.values, three.values)
    assert np.array_equal(one.temporal_valid, three.temporal_valid)
