from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

import cv2
import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from sieve.backend.dispatch import Backend, stateful_kernel
from sieve.core.filter_base import (
    ArraySpec,
    CostEstimate,
    ElementKind,
    Mode,
    ParamsBase,
)
from sieve.core.filter_registry import register_filter
from sieve.core.types import ChannelSpec, Frame


SIGMA = 2.0


DET_EPS = 1e-6


AUTO_BLOCK_SOURCE_PX = 64

SUPPORTED_DTYPES = ("uint8", "uint16", "float32", "float64")

FloatArray = NDArray[np.floating[Any]]


def auto_block(scale: float) -> int:
    return max(1, round(AUTO_BLOCK_SOURCE_PX * scale))


def resolve_block(block: int, scale: float) -> int:
    return block if block > 0 else auto_block(scale)


def grid_shape(height: int, width: int, block: int) -> tuple[int, int]:
    return -(-height // block), -(-width // block)


class Signal(StrEnum):
    CHANGE_ENERGY = "change_energy"

    FLOW_SPEED = "flow_speed"

    COHERENCE = "coherence"

    FLOW_AGREEMENT = "flow_agreement"


@register_filter(
    filter_id="block_signal",
    version="1.0.0",
    summary="Per-block motion signal from the structure tensor of consecutive frames.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),
    emits=ArraySpec(dtypes=("float32",), channels=(ChannelSpec.GRAY,)),
    element=ElementKind.BLOCK,
    cost=CostEstimate(
        seconds_per_megapixel=0.012,
        peak_bytes_per_input_byte=12.0,
    ),
    mode=Mode.STREAMING,
    warmup_frames=1,
    stateful=True,
    primary_params=("signal", "block"),
)
class BlockSignalParams(ParamsBase):
    signal: Signal = Signal.CHANGE_ENERGY

    block: int = Field(default=0, ge=0, le=1024)

    scale: float = Field(default=1.0, ge=0.05, le=1.0)

    fps: float = Field(default=30.0, gt=0.0)

    def frame_bytes_ratio(self) -> float:
        return 1.0 / resolve_block(self.block, self.scale) ** 2


@dataclass(slots=True)
class BlockSignalState:
    prev: FloatArray | None = None


@stateful_kernel(BlockSignalParams, Backend.CPU, state=BlockSignalState)
def block_signal_cpu(
    frame: Frame, params: BlockSignalParams, state: BlockSignalState
) -> Frame:
    gray = _to_gray(frame)
    block = resolve_block(params.block, params.scale)
    ny, nx = grid_shape(gray.shape[0], gray.shape[1], block)
    prev = state.prev
    state.prev = gray
    if prev is None:
        out = np.zeros((ny, nx), np.float32)
    elif prev.shape != gray.shape:
        raise ValueError(
            f"block_signal saw a {prev.shape} frame and then a {gray.shape} one at "
            f"index {frame.index}; one run is one geometry"
        )
    elif params.signal is Signal.CHANGE_ENERGY:
        it = gray - prev
        out = _block_mean(_blur(it * it), block, ny, nx)
    elif params.signal is Signal.COHERENCE:
        out = _coherence(prev, gray, block, ny, nx)
    elif params.signal is Signal.FLOW_AGREEMENT:
        out = _flow_agreement(prev, gray, block, ny, nx)
    else:
        out = _block_mean(_flow_speed(prev, gray, params.fps), block, ny, nx)
    return Frame(data=out, index=frame.index, channels=ChannelSpec.GRAY)


def _to_gray(frame: Frame) -> NDArray[np.float32]:
    data = np.asarray(frame.data, np.float32)
    if frame.channels is ChannelSpec.GRAY:
        return data
    code = (
        cv2.COLOR_BGR2GRAY if frame.channels is ChannelSpec.BGR else cv2.COLOR_RGB2GRAY
    )
    return cast(NDArray[np.float32], cv2.cvtColor(data, code))


def _blur(plane: FloatArray) -> NDArray[np.float32]:
    return cast(NDArray[np.float32], cv2.GaussianBlur(plane, (0, 0), SIGMA))


def _lk_flow(
    prev: FloatArray, gray: FloatArray
) -> tuple[NDArray[np.float32], NDArray[np.float32], NDArray[np.bool_]]:
    it = gray - prev
    grads = np.gradient(gray)
    iy = np.asarray(grads[0], np.float32)
    ix = np.asarray(grads[1], np.float32)
    xx = _blur(ix * ix)
    yy = _blur(iy * iy)
    xy = _blur(ix * iy)
    xt = _blur(ix * it)
    yt = _blur(iy * it)
    det = xx * yy - xy * xy
    safe = np.abs(det) > DET_EPS
    inv = np.where(safe, 1.0 / np.where(safe, det, 1.0), 0.0)
    u = (-(yy * xt - xy * yt) * inv).astype(np.float32)
    v = (-(xx * yt - xy * xt) * inv).astype(np.float32)
    return u, v, safe


def _flow_speed(prev: FloatArray, gray: FloatArray, fps: float) -> NDArray[np.float32]:
    u, v, _ = _lk_flow(prev, gray)
    return (np.hypot(u, v) * fps).astype(np.float32)


def _flow_agreement(
    prev: FloatArray, gray: FloatArray, block: int, ny: int, nx: int
) -> NDArray[np.float32]:
    u, v, safe = _lk_flow(prev, gray)
    speed = np.hypot(u, v)
    moving = safe & (speed > 0.0)
    scale = np.where(moving, 1.0 / np.where(moving, speed, 1.0), 0.0)
    sum_x = _block_mean((u * scale).astype(np.float32), block, ny, nx)
    sum_y = _block_mean((v * scale).astype(np.float32), block, ny, nx)
    share = _block_mean(moving.astype(np.float32), block, ny, nx)
    ok = share > 0.0
    inv_share = np.where(ok, 1.0 / np.where(ok, share, 1.0), 0.0)
    return np.minimum(np.hypot(sum_x * inv_share, sum_y * inv_share), 1.0).astype(
        np.float32
    )


def _coherence(
    prev: FloatArray, gray: FloatArray, block: int, ny: int, nx: int
) -> NDArray[np.float32]:
    it = gray - prev
    grads = np.gradient(gray)
    iy = np.asarray(grads[0], np.float32)
    ix = np.asarray(grads[1], np.float32)
    tensor = np.empty((ny, nx, 3, 3), np.float32)
    products: dict[tuple[int, int], FloatArray] = {
        (0, 0): ix * ix,
        (1, 1): iy * iy,
        (2, 2): it * it,
        (0, 1): ix * iy,
        (0, 2): ix * it,
        (1, 2): iy * it,
    }
    for (row, col), plane in products.items():
        reduced = _block_mean(_blur(plane), block, ny, nx)
        tensor[:, :, row, col] = reduced
        tensor[:, :, col, row] = reduced
    lam = np.maximum(np.linalg.eigvalsh(tensor), 0.0)
    lam3, lam2 = lam[..., 0], lam[..., 1]
    denom = lam2 + lam3
    safe = denom > 0.0
    coh = np.where(safe, ((lam2 - lam3) / np.where(safe, denom, 1.0)) ** 2, 0.0)
    return np.where(tensor[:, :, 2, 2] > 0.0, coh, 0.0).astype(np.float32)


def _block_mean(field: FloatArray, block: int, ny: int, nx: int) -> NDArray[np.float32]:
    h, w = field.shape
    f32 = field.astype(np.float32, copy=False)
    if ny * block == h and nx * block == w:
        return f32.reshape(ny, block, nx, block).mean(axis=(1, 3), dtype=np.float32)
    padded = np.pad(
        f32, ((0, ny * block - h), (0, nx * block - w)), constant_values=np.nan
    )
    cells = padded.reshape(ny, block, nx, block).transpose(0, 2, 1, 3)
    return np.nanmean(cells.reshape(ny, nx, block * block), axis=2).astype(np.float32)
