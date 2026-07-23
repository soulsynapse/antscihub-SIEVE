from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from antscihub_sieve.application.resources import (
    ExecutionResourcePolicy,
    ExecutionTarget,
)
from antscihub_sieve.application.working_grid import ResolvedWorkingGrid
from antscihub_sieve.application.working_window import (
    PlaneDescriptor,
    ResolvedWorkingWindow,
    WorkingWindowOutcome,
    WorkingWindowOutcomeKind,
    WorkingWindowRequest,
    WorkingWindowStream,
    open_working_window,
)
from antscihub_sieve.errors import SieveError


CHANNEL_ID = "intensity"
INTENSITY_CONVERSION_ID = "sieve.channel.rgb601_intensity.v1"
NORMALIZATION_ID = "off"
IMPLEMENTATION_ID = "sieve.numpy.area_block_mean.v1"

Float32Array = NDArray[np.float32]
ProgressCallback = Callable[[int, int], None]
CancellationPredicate = Callable[[], bool]


class ChannelStageOutcome(str, Enum):
    COMPLETED = "completed"
    COMPUTATION_FAILED = "computation_failed"


@dataclass(frozen=True, slots=True)
class IntensityRequest:
    working_window: WorkingWindowRequest
    grid: ResolvedWorkingGrid
    resources: ExecutionResourcePolicy = ExecutionResourcePolicy()
    execution_target: ExecutionTarget = ExecutionTarget.CPU
    batch_size: int = 1

    def __post_init__(self) -> None:
        if self.execution_target is not ExecutionTarget.CPU:
            raise ValueError(
                "The first intensity channel currently supports CPU execution only"
            )
        if (
            isinstance(self.batch_size, bool)
            or not isinstance(self.batch_size, int)
            or self.batch_size < 1
        ):
            raise ValueError("batch_size must be a positive integer")


@dataclass(frozen=True, slots=True)
class IntensityResult:
    request: IntensityRequest
    resolved_window: ResolvedWorkingWindow
    plane: PlaneDescriptor
    values: Float32Array
    source_outcome: WorkingWindowOutcome
    channel_outcome: ChannelStageOutcome
    processed_start: int
    processed_stop: int
    frame_indices: tuple[int, ...]
    partial_cell_weights: tuple[float, ...]
    estimated_result_bytes: int
    conversion_id: str = INTENSITY_CONVERSION_ID
    normalization_id: str = NORMALIZATION_ID
    implementation_id: str = IMPLEMENTATION_ID
    backend: str = f"numpy-{np.__version__}"
    error: SieveError | None = None

    @property
    def complete(self) -> bool:
        requested = self.request.working_window
        return (
            self.source_outcome.kind is WorkingWindowOutcomeKind.COMPLETE
            and self.channel_outcome is ChannelStageOutcome.COMPLETED
            and self.processed_start == requested.start_frame
            and self.processed_stop == requested.stop_frame
            and self.values.shape
            == (
                requested.stop_frame - requested.start_frame,
                self.request.grid.rows,
                self.request.grid.columns,
            )
        )


class StreamFactory(Protocol):
    def __call__(
        self,
        request: WorkingWindowRequest,
        *,
        batch_size: int,
        cancelled: CancellationPredicate | None,
    ) -> WorkingWindowStream: ...


def estimate_result_bytes(request: IntensityRequest) -> int:
    frames = (
        request.working_window.stop_frame
        - request.working_window.start_frame
    )
    if frames < 1:
        raise SieveError(
            "INTENSITY_REQUEST_INVALID",
            "Intensity requires a nonempty half-open frame span",
            start_frame=request.working_window.start_frame,
            stop_frame=request.working_window.stop_frame,
        )
    return frames * request.grid.rows * request.grid.columns * 4


def admit_result_memory(request: IntensityRequest) -> int:
    requested_bytes = estimate_result_bytes(request)
    allowed_bytes = request.resources.result_memory_limit(
        request.execution_target
    )
    if requested_bytes > allowed_bytes:
        raise SieveError(
            "RESOURCE_RESULT_MEMORY_EXCEEDED",
            "Intensity result exceeds the configured result-memory budget",
            requested_bytes=requested_bytes,
            allowed_bytes=allowed_bytes,
            target=request.execution_target.value,
            shape=(
                request.working_window.stop_frame
                - request.working_window.start_frame,
                request.grid.rows,
                request.grid.columns,
            ),
        )
    return requested_bytes


def compute_intensity(
    request: IntensityRequest,
    *,
    cancelled: CancellationPredicate | None = None,
    progress: ProgressCallback | None = None,
    stream_factory: StreamFactory = open_working_window,
) -> IntensityResult:
    estimated_bytes = admit_result_memory(request)
    if cancelled is not None and cancelled():
        raise SieveError(
            "INTENSITY_CANCELLED",
            "Intensity computation was cancelled before source construction",
        )

    stream = stream_factory(
        request.working_window,
        batch_size=request.batch_size,
        cancelled=cancelled,
    )
    resolved = stream.resolved
    total = request.working_window.stop_frame - request.working_window.start_frame
    retained: Float32Array | None = None
    processed_indices: list[int] = []
    stage = ChannelStageOutcome.COMPLETED
    computation_error: SieveError | None = None

    try:
        _validate_source_geometry(resolved, request.grid)
        retained = np.empty(
            (total, request.grid.rows, request.grid.columns),
            dtype=np.float32,
        )
        for batch in stream:
            for absolute_frame, raw in zip(
                batch.absolute_frame_indices,
                batch.frame_buffers,
                strict=True,
            ):
                expected_frame = (
                    request.working_window.start_frame
                    + len(processed_indices)
                )
                if absolute_frame != expected_frame:
                    raise SieveError(
                        "INTENSITY_SOURCE_INVALID",
                        "Intensity source frames must be contiguous and ordered",
                        expected_frame=expected_frame,
                        actual_frame=absolute_frame,
                    )
                retained[len(processed_indices)] = reduce_rgb_frame(
                    raw,
                    batch.plane,
                    request.grid,
                )
                processed_indices.append(absolute_frame)
                if progress is not None:
                    progress(len(processed_indices), total)
    except SieveError as exc:
        if stream.outcome is None:
            stage = ChannelStageOutcome.COMPUTATION_FAILED
            computation_error = exc
        elif stream.outcome.kind is WorkingWindowOutcomeKind.FAILED:
            computation_error = stream.outcome.error or exc
        else:
            stage = ChannelStageOutcome.COMPUTATION_FAILED
            computation_error = exc
    except BaseException as exc:
        if (
            stream.outcome is not None
            and stream.outcome.kind is WorkingWindowOutcomeKind.FAILED
        ):
            computation_error = stream.outcome.error or SieveError(
                "WORKING_WINDOW_FAILED",
                "Working-window source failed",
                exception_type=type(exc).__name__,
                detail=str(exc),
            )
        else:
            stage = ChannelStageOutcome.COMPUTATION_FAILED
            computation_error = SieveError(
                "INTENSITY_COMPUTATION_FAILED",
                "Intensity computation failed",
                exception_type=type(exc).__name__,
                detail=str(exc),
            )
    finally:
        stream.close()

    outcome = stream.outcome
    if outcome is None:
        raise RuntimeError("Working-window stream closed without an outcome")
    if retained is None:
        retained = np.empty(
            (0, request.grid.rows, request.grid.columns),
            dtype=np.float32,
        )
    values = retained[: len(processed_indices)].copy()
    values.setflags(write=False)
    start = request.working_window.start_frame
    stop = start + len(processed_indices)
    return IntensityResult(
        request=request,
        resolved_window=resolved,
        plane=resolved.plane,
        values=values,
        source_outcome=outcome,
        channel_outcome=stage,
        processed_start=start,
        processed_stop=stop,
        frame_indices=tuple(processed_indices),
        partial_cell_weights=_partial_cell_weights(request.grid),
        estimated_result_bytes=estimated_bytes,
        error=computation_error,
    )


def reduce_rgb_frame(
    raw: bytes,
    plane: PlaneDescriptor,
    grid: ResolvedWorkingGrid,
) -> Float32Array:
    expected_bytes = plane.width * plane.height * 3
    if (
        plane.plane_id != "rgb24"
        or plane.channels != 3
        or plane.dtype != "uint8"
        or plane.channel_order != ("R", "G", "B")
        or len(raw) != expected_bytes
    ):
        raise SieveError(
            "INTENSITY_SOURCE_INVALID",
            "Intensity requires exact native-resolution decoded rgb24 frames",
            expected_bytes=expected_bytes,
            actual_bytes=len(raw),
            plane_id=plane.plane_id,
            channels=plane.channels,
            dtype=plane.dtype,
            channel_order=plane.channel_order,
        )
    if (
        plane.width != grid.source_width
        or plane.height != grid.source_height
    ):
        raise SieveError(
            "INTENSITY_GEOMETRY_MISMATCH",
            "Decoded source dimensions do not match the captured working grid",
            decoded_width=plane.width,
            decoded_height=plane.height,
            grid_width=grid.source_width,
            grid_height=grid.source_height,
        )

    rgb = np.frombuffer(raw, dtype=np.uint8).reshape(
        plane.height, plane.width, 3
    )
    intensity = (
        rgb[..., 0].astype(np.float64) * 0.299
        + rgb[..., 1].astype(np.float64) * 0.587
        + rgb[..., 2].astype(np.float64) * 0.114
    ) / 255.0
    working = area_downsample(
        intensity,
        grid.work_height,
        grid.work_width,
    )
    blocks = np.empty((grid.rows, grid.columns), dtype=np.float32)
    for row in range(grid.rows):
        for column in range(grid.columns):
            bounds = grid.block_bounds(row, column)
            value = np.mean(
                working[bounds.y0 : bounds.y1, bounds.x0 : bounds.x1],
                dtype=np.float64,
            )
            if not np.isfinite(value):
                raise SieveError(
                    "INTENSITY_NONFINITE",
                    "Intensity reduction produced a non-finite value",
                    row=row,
                    column=column,
                )
            blocks[row, column] = value
    return blocks


def area_downsample(
    source: NDArray[np.floating],
    output_height: int,
    output_width: int,
) -> Float32Array:
    if source.ndim != 2:
        raise ValueError("Area downsampling requires a two-dimensional plane")
    source_height, source_width = source.shape
    if (
        output_height < 1
        or output_width < 1
        or output_height > source_height
        or output_width > source_width
    ):
        raise ValueError(
            "Area downsampling output must be nonempty and no larger than input"
        )
    work = source.astype(np.float64, copy=False)
    if output_width != source_width:
        work = _area_axis(work, output_width, axis=1)
    if output_height != source_height:
        work = _area_axis(work, output_height, axis=0)
    result = work.astype(np.float32)
    if not np.all(np.isfinite(result)):
        raise SieveError(
            "INTENSITY_NONFINITE",
            "Area downsampling produced non-finite values",
        )
    return result


def _area_axis(
    source: NDArray[np.float64],
    output_size: int,
    *,
    axis: int,
) -> NDArray[np.float64]:
    source_size = source.shape[axis]
    edges = np.arange(output_size + 1, dtype=np.float64)
    edges *= source_size / output_size
    indices = np.floor(edges).astype(np.int64)
    fractions = edges - indices
    clipped = np.minimum(indices, source_size - 1)

    prefix = np.cumsum(source, axis=axis, dtype=np.float64)
    pad_shape = list(prefix.shape)
    pad_shape[axis] = 1
    prefix = np.concatenate(
        [np.zeros(pad_shape, dtype=np.float64), prefix],
        axis=axis,
    )
    integrals = np.take(prefix, indices, axis=axis)
    edge_values = np.take(source, clipped, axis=axis)
    shape = [1] * source.ndim
    shape[axis] = output_size + 1
    integrals = integrals + edge_values * fractions.reshape(shape)
    return np.diff(integrals, axis=axis) / (source_size / output_size)


def _validate_source_geometry(
    resolved: ResolvedWorkingWindow,
    grid: ResolvedWorkingGrid,
) -> None:
    if (
        resolved.width != grid.source_width
        or resolved.height != grid.source_height
    ):
        raise SieveError(
            "INTENSITY_GEOMETRY_MISMATCH",
            "Probed source dimensions do not match the captured working grid",
            probed_width=resolved.width,
            probed_height=resolved.height,
            grid_width=grid.source_width,
            grid_height=grid.source_height,
        )


def _partial_cell_weights(grid: ResolvedWorkingGrid) -> tuple[float, ...]:
    return tuple(
        grid.block_area_weight(row, column)
        for row in range(grid.rows)
        for column in range(grid.columns)
    )
