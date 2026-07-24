from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Protocol

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from numpy.typing import NDArray

from antscihub_sieve.application.channel_progress import (
    ChannelFrame,
    FrameCompletedCallback,
)
from antscihub_sieve.application.intensity import (
    ChannelStageOutcome,
    Float32Array,
    IMPLEMENTATION_ID as BLOCK_REDUCTION_ID,
    INTENSITY_CONVERSION_ID,
    NormalizationMode,
    NormalizationSpec,
    UInt8Array,
    normalize_working_frame,
    reduce_working_frame,
    working_intensity_frame,
)
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


CHANNEL_ID = "change_energy"
CHANGE_ENERGY_ID = "sieve.channel.rgb601_change_energy.v1"
TEMPORAL_DIFFERENCE_ID = "sieve.temporal.current_minus_previous_square.v1"
GAUSSIAN_INTEGRATION_ID = (
    "sieve.spatial.gaussian_sigma2_reflect101.v1"
)
IMPLEMENTATION_ID = "sieve.numpy.change_energy.v1"
AREA_DOWNSAMPLE_ID = "sieve.numpy.area_downsample.v1"
GAUSSIAN_SIGMA = 2.0
GAUSSIAN_RADIUS = 8
OFF_UNITS = "post-decoder intensity squared"
ZSCORE_UNITS = "z-score squared"

Int8Array = NDArray[np.int8]
ProgressCallback = Callable[[int, int], None]
CancellationPredicate = Callable[[], bool]


@dataclass(frozen=True, slots=True)
class SpatialIntegrationSpec:
    sigma_x: float = GAUSSIAN_SIGMA
    sigma_y: float = GAUSSIAN_SIGMA
    radius: int = GAUSSIAN_RADIUS
    border_mode: str = "reflect101"
    implementation_id: str = GAUSSIAN_INTEGRATION_ID

    def __post_init__(self) -> None:
        if (
            self.sigma_x != GAUSSIAN_SIGMA
            or self.sigma_y != GAUSSIAN_SIGMA
            or self.radius != GAUSSIAN_RADIUS
            or self.border_mode != "reflect101"
            or self.implementation_id != GAUSSIAN_INTEGRATION_ID
        ):
            raise ValueError(
                "Milestone 7 supports only the fixed sigma-2 reflect-101 "
                "Gaussian integration"
            )


@dataclass(frozen=True, slots=True)
class ChangeEnergyScientificKey:
    working_window: WorkingWindowRequest
    grid: ResolvedWorkingGrid
    normalization: NormalizationSpec
    integration: SpatialIntegrationSpec
    intensity_conversion_id: str = INTENSITY_CONVERSION_ID
    area_downsample_id: str = AREA_DOWNSAMPLE_ID
    block_reduction_id: str = BLOCK_REDUCTION_ID
    temporal_difference_id: str = TEMPORAL_DIFFERENCE_ID
    channel_implementation_id: str = IMPLEMENTATION_ID


@dataclass(frozen=True, slots=True)
class ChangeEnergyRequest:
    working_window: WorkingWindowRequest
    grid: ResolvedWorkingGrid
    normalization: NormalizationSpec = NormalizationSpec()
    integration: SpatialIntegrationSpec = SpatialIntegrationSpec()
    resources: ExecutionResourcePolicy = ExecutionResourcePolicy()
    execution_target: ExecutionTarget = ExecutionTarget.CPU
    batch_size: int = 1

    def __post_init__(self) -> None:
        if self.execution_target is not ExecutionTarget.CPU:
            raise ValueError("Change energy currently supports CPU execution only")
        if (
            isinstance(self.batch_size, bool)
            or not isinstance(self.batch_size, int)
            or self.batch_size < 1
        ):
            raise ValueError("batch_size must be a positive integer")

    @property
    def scientific_key(self) -> ChangeEnergyScientificKey:
        return ChangeEnergyScientificKey(
            working_window=self.working_window,
            grid=self.grid,
            normalization=self.normalization,
            integration=self.integration,
        )

    @property
    def source_request(self) -> WorkingWindowRequest:
        return replace(
            self.working_window,
            start_frame=max(0, self.working_window.start_frame - 1),
        )


@dataclass(frozen=True, slots=True)
class ChangeEnergyResult:
    request: ChangeEnergyRequest
    resolved_window: ResolvedWorkingWindow
    plane: PlaneDescriptor
    values: Float32Array
    temporal_valid: UInt8Array
    previous_degenerate: Int8Array
    current_degenerate: UInt8Array
    source_outcome: WorkingWindowOutcome
    channel_outcome: ChannelStageOutcome
    processed_start: int
    processed_stop: int
    valid_start: int
    valid_stop: int
    partial_cell_weights: tuple[float, ...]
    estimated_result_bytes: int
    scientific_units: str
    normalization_backend: str
    integration_id: str = GAUSSIAN_INTEGRATION_ID
    temporal_difference_id: str = TEMPORAL_DIFFERENCE_ID
    conversion_id: str = INTENSITY_CONVERSION_ID
    area_downsample_id: str = AREA_DOWNSAMPLE_ID
    block_reduction_id: str = BLOCK_REDUCTION_ID
    implementation_id: str = IMPLEMENTATION_ID
    backend: str = f"numpy-{np.__version__}"
    error: SieveError | None = None

    @property
    def complete(self) -> bool:
        requested = self.request.working_window
        total = requested.stop_frame - requested.start_frame
        expected_valid = np.fromiter(
            (frame > 0 for frame in range(requested.start_frame, requested.stop_frame)),
            dtype=np.uint8,
            count=total,
        )
        return (
            self.source_outcome.kind is WorkingWindowOutcomeKind.COMPLETE
            and self.channel_outcome is ChannelStageOutcome.COMPLETED
            and self.processed_start == requested.start_frame
            and self.processed_stop == requested.stop_frame
            and self.values.shape
            == (total, self.request.grid.rows, self.request.grid.columns)
            and np.array_equal(self.temporal_valid, expected_valid)
            and self.previous_degenerate.shape == (total,)
            and self.current_degenerate.shape == (total,)
        )

    @property
    def scientific_key(self) -> ChangeEnergyScientificKey:
        return self.request.scientific_key

    @property
    def normalization_id(self) -> str:
        return self.request.normalization.implementation_id


class StreamFactory(Protocol):
    def __call__(
        self,
        request: WorkingWindowRequest,
        *,
        batch_size: int,
        cancelled: CancellationPredicate | None,
    ) -> WorkingWindowStream: ...


def estimate_result_bytes(request: ChangeEnergyRequest) -> int:
    frames = request.working_window.stop_frame - request.working_window.start_frame
    if frames < 1:
        raise SieveError(
            "CHANGE_ENERGY_REQUEST_INVALID",
            "Change energy requires a nonempty half-open frame span",
            start_frame=request.working_window.start_frame,
            stop_frame=request.working_window.stop_frame,
        )
    # float32 values plus temporal-valid, previous-degenerate, and
    # current-degenerate one-byte arrays. Absolute indices are represented by
    # the retained half-open span rather than a materialized array.
    return frames * request.grid.rows * request.grid.columns * 4 + frames * 3


def admit_result_memory(request: ChangeEnergyRequest) -> int:
    requested_bytes = estimate_result_bytes(request)
    allowed_bytes = request.resources.result_memory_limit(
        request.execution_target
    )
    if requested_bytes > allowed_bytes:
        raise SieveError(
            "RESOURCE_RESULT_MEMORY_EXCEEDED",
            "Change-energy result exceeds the configured result-memory budget",
            requested_bytes=requested_bytes,
            allowed_bytes=allowed_bytes,
            target=request.execution_target.value,
        )
    return requested_bytes


def gaussian_kernel() -> NDArray[np.float64]:
    offsets = np.arange(
        -GAUSSIAN_RADIUS, GAUSSIAN_RADIUS + 1, dtype=np.float64
    )
    kernel = np.exp(-0.5 * (offsets / GAUSSIAN_SIGMA) ** 2)
    kernel /= np.sum(kernel, dtype=np.float64)
    kernel.setflags(write=False)
    return kernel


def gaussian_integrate(field: Float32Array) -> Float32Array:
    if field.ndim != 2 or field.dtype != np.float32:
        raise SieveError(
            "CHANGE_ENERGY_INTEGRATION_INVALID",
            "Gaussian integration requires a two-dimensional float32 field",
            shape=field.shape,
            dtype=str(field.dtype),
            stage="gaussian_integration",
        )
    if not np.all(np.isfinite(field)) or np.any(field < 0):
        raise SieveError(
            "CHANGE_ENERGY_NONFINITE",
            "Gaussian integration requires finite nonnegative energy",
            stage="gaussian_integration",
        )
    kernel = gaussian_kernel()
    work = field.astype(np.float64, copy=False)
    horizontal = _convolve_reflect101(work, kernel, axis=1)
    integrated = _convolve_reflect101(horizontal, kernel, axis=0)
    result = integrated.astype(np.float32)
    if not np.all(np.isfinite(result)) or np.any(result < 0):
        raise SieveError(
            "CHANGE_ENERGY_NONFINITE",
            "Gaussian integration produced invalid energy",
            stage="gaussian_integration",
        )
    return result


def _convolve_reflect101(
    source: NDArray[np.float64],
    kernel: NDArray[np.float64],
    *,
    axis: int,
) -> NDArray[np.float64]:
    radius = len(kernel) // 2
    if source.shape[axis] == 1:
        pad_mode = "edge"
    else:
        pad_mode = "reflect"
    pads = [(0, 0)] * source.ndim
    pads[axis] = (radius, radius)
    padded = np.pad(source, pads, mode=pad_mode)
    windows = sliding_window_view(padded, len(kernel), axis=axis)
    return np.tensordot(windows, kernel, axes=([-1], [0]))


def change_energy_pair(
    previous: Float32Array,
    current: Float32Array,
    grid: ResolvedWorkingGrid,
) -> Float32Array:
    if previous.shape != current.shape or previous.shape != (
        grid.work_height,
        grid.work_width,
    ):
        raise SieveError(
            "CHANGE_ENERGY_GEOMETRY_MISMATCH",
            "Temporal pair does not match the captured working grid",
            previous_shape=previous.shape,
            current_shape=current.shape,
            expected_shape=(grid.work_height, grid.work_width),
            stage="temporal_difference",
        )
    difference = np.subtract(current, previous, dtype=np.float32)
    energy = np.multiply(difference, difference, dtype=np.float32)
    if not np.all(np.isfinite(energy)) or np.any(energy < 0):
        raise SieveError(
            "CHANGE_ENERGY_NONFINITE",
            "Temporal difference produced invalid energy",
            stage="temporal_difference",
        )
    return reduce_working_frame(gaussian_integrate(energy), grid)


def compute_change_energy(
    request: ChangeEnergyRequest,
    *,
    cancelled: CancellationPredicate | None = None,
    progress: ProgressCallback | None = None,
    frame_completed: FrameCompletedCallback | None = None,
    stream_factory: StreamFactory = open_working_window,
) -> ChangeEnergyResult:
    estimated_bytes = admit_result_memory(request)
    if cancelled is not None and cancelled():
        raise SieveError(
            "CHANGE_ENERGY_CANCELLED",
            "Change energy was cancelled before source construction",
        )

    stream = stream_factory(
        request.source_request,
        batch_size=request.batch_size,
        cancelled=cancelled,
    )
    resolved = stream.resolved
    output = request.working_window
    total = output.stop_frame - output.start_frame
    values = np.zeros(
        (total, request.grid.rows, request.grid.columns), dtype=np.float32
    )
    temporal_valid = np.zeros(total, dtype=np.uint8)
    previous_degenerate = np.full(total, -1, dtype=np.int8)
    current_degenerate = np.zeros(total, dtype=np.uint8)
    delivered: list[int] = []
    produced: list[int] = []
    previous_frame: int | None = None
    previous_working: Float32Array | None = None
    previous_was_degenerate = False
    stage = ChannelStageOutcome.COMPLETED
    computation_error: SieveError | None = None

    try:
        if (
            resolved.width != request.grid.source_width
            or resolved.height != request.grid.source_height
        ):
            raise SieveError(
                "CHANGE_ENERGY_GEOMETRY_MISMATCH",
                "Source dimensions do not match the captured working grid",
                stage="source_validation",
            )
        for batch in stream:
            for absolute_frame, raw in zip(
                batch.absolute_frame_indices,
                batch.frame_buffers,
                strict=True,
            ):
                expected = request.source_request.start_frame + len(delivered)
                if absolute_frame != expected:
                    raise SieveError(
                        "CHANGE_ENERGY_SOURCE_INVALID",
                        "Change-energy source frames must be contiguous and ordered",
                        expected_frame=expected,
                        actual_frame=absolute_frame,
                    )
                if cancelled is not None and cancelled():
                    raise SieveError(
                        "CHANGE_ENERGY_CANCELLED",
                        "Change energy was cancelled between temporal frames",
                        absolute_frame=absolute_frame,
                    )
                working = working_intensity_frame(raw, batch.plane, request.grid)
                normalized, degenerate = normalize_working_frame(
                    working, request.normalization
                )
                delivered.append(absolute_frame)
                if output.start_frame <= absolute_frame < output.stop_frame:
                    offset = absolute_frame - output.start_frame
                    current_degenerate[offset] = int(degenerate)
                    if absolute_frame == 0:
                        produced.append(absolute_frame)
                    elif (
                        previous_frame == absolute_frame - 1
                        and previous_working is not None
                    ):
                        previous_degenerate[offset] = int(
                            previous_was_degenerate
                        )
                        values[offset] = change_energy_pair(
                            previous_working, normalized, request.grid
                        )
                        temporal_valid[offset] = 1
                        produced.append(absolute_frame)
                    else:
                        raise SieveError(
                            "CHANGE_ENERGY_PREDECESSOR_MISSING",
                            "Required predecessor was not delivered",
                            output_frame=absolute_frame,
                            expected_predecessor=absolute_frame - 1,
                        )
                    if frame_completed is not None:
                        frame_completed(
                            ChannelFrame(
                                absolute_frame=absolute_frame,
                                values=values[offset],
                                valid=bool(temporal_valid[offset]),
                            )
                        )
                    if progress is not None:
                        progress(len(produced), total)
                previous_frame = absolute_frame
                previous_working = normalized
                previous_was_degenerate = degenerate
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
        stage = ChannelStageOutcome.COMPUTATION_FAILED
        computation_error = SieveError(
            "CHANGE_ENERGY_COMPUTATION_FAILED",
            "Change-energy computation failed",
            exception_type=type(exc).__name__,
            detail=str(exc),
        )
    finally:
        stream.close()

    outcome = stream.outcome
    if outcome is None:
        raise RuntimeError("Working-window stream closed without an outcome")
    processed_count = len(produced)
    processed_stop = output.start_frame + processed_count
    valid_indices = [
        output.start_frame + index
        for index, valid in enumerate(temporal_valid[:processed_count])
        if valid
    ]
    for array in (
        values,
        temporal_valid,
        previous_degenerate,
        current_degenerate,
    ):
        array.setflags(write=False)
    units = (
        OFF_UNITS
        if request.normalization.mode is NormalizationMode.OFF
        else ZSCORE_UNITS
    )
    return ChangeEnergyResult(
        request=request,
        resolved_window=resolved,
        plane=resolved.plane,
        values=values,
        temporal_valid=temporal_valid,
        previous_degenerate=previous_degenerate,
        current_degenerate=current_degenerate,
        source_outcome=outcome,
        channel_outcome=stage,
        processed_start=output.start_frame,
        processed_stop=processed_stop,
        valid_start=valid_indices[0] if valid_indices else processed_stop,
        valid_stop=(valid_indices[-1] + 1) if valid_indices else processed_stop,
        partial_cell_weights=tuple(
            request.grid.block_area_weight(row, column)
            for row in range(request.grid.rows)
            for column in range(request.grid.columns)
        ),
        estimated_result_bytes=estimated_bytes,
        scientific_units=units,
        normalization_backend=f"numpy-{np.__version__}",
        error=computation_error,
    )
