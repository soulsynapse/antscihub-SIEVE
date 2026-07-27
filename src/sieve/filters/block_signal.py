"""Per-block motion signals from the structure tensor of consecutive frames.

The extraction step of the live tab: each output frame is a small `(ny, nx)`
GRAY float32 grid, one value per block, and the *series* of those frames is
what the temporal filter and detector consume. Ported from v1
(`antscihub-optical-flow-detector`, `core/{tensor_channels,structure_tensor}.py`)
semantics-intact:

* `it = g - gp` (one-frame forward difference), `iy, ix = np.gradient(g)`
  (central differences), products Gaussian-blurred with **sigma = 2.0** — the
  blur *is* the tensor's spatial window — then block-mean reduced.
* **change_energy** (v1 "change", Jtt): the blurred `<I_t^2>` plane. One
  product, one blur, the cheapest signal — v1 streamed it live always.
* **flow_speed** (v1 "tensor_speed"): the per-pixel 2x2 Lucas-Kanade solve
  `[[Jxx, Jxy], [Jxy, Jyy]] v = -[Jxt, Jyt]`, with `|det| <= 1e-6 -> v = 0`
  (aperture-degenerate pixels honestly zero rather than a near-zero divide),
  speed `hypot(u, v) * fps` in px/s, *then* block-reduced. The solve precedes
  reduction so the aperture problem is not coupled to the user's block size.
  Needs all six products, ~4x change_energy's cost.
* **coherence** (new in SIEVE): all six components block-reduced into one
  3x3 tensor per block, then eigendecomposed — reduction *precedes* the
  decomposition, the mirror of flow_speed's constraint, because a per-pixel
  tensor is near rank-one and only block aggregation of mixed orientations
  makes the spectrum informative. Emits Haussecker & Spies' spatial
  coherency `((lam2 - lam3) / (lam2 + lam3))^2` in [0, 1]: a single
  translation explains the block's change iff the tensor has a null
  direction (lam3 ~ 0), so walking reads near 1 and in-place change
  (grooming, flicker) near 0. Same six blurs as flow_speed plus a few
  hundred 3x3 eigensolves.

One filter with a `signal` parameter rather than two filters: the two share
the state, the gradient, and the reduction, and the tab's quick-switch swaps
the parameter in place — the same step card, the same bands.

**Block resolution lives in exactly one exported function.** `0 = auto` means
`max(1, round(64 source px x scale))`: the grid is held fixed in *source*
pixels, so turning the rescale knob changes compute cost, not where a
detection localizes. `scale` and `fps` are explicit parameters because the
kernel must stay pure — it cannot ask the graph what the upstream rescale did
or what the container's frame rate is; the tab writes both from the values it
already owns.

Stateful (the previous frame is the state), `warmup_frames = 1`, and
therefore uncacheable — the `background_ema` reasoning applies verbatim.
Extraction at working resolution is ~realtime, so recomputation is the cheap
side of that trade.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

import cv2
import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from sieve.backend.dispatch import Backend, stateful_kernel
from sieve.core.filter_base import ArraySpec, CostEstimate, Mode, ParamsBase
from sieve.core.filter_registry import register_filter
from sieve.core.types import ChannelSpec, Frame

#: The tensor window, in working pixels. v1's constant: every measured band
#: and threshold in every v1 session was tuned against this blur, so it is
#: part of the parity semantic rather than a knob.
SIGMA = 2.0

#: Below this spatial determinant the LK system is aperture-degenerate and
#: the solve returns exactly zero flow. v1's cutoff.
DET_EPS = 1e-6

#: The auto block size in *source* pixels. 64 was v1's default working value;
#: `auto_block` scales it so the grid stays fixed in source coordinates.
AUTO_BLOCK_SOURCE_PX = 64

SUPPORTED_DTYPES = ("uint8", "uint16", "float32", "float64")

FloatArray = NDArray[np.floating[Any]]


def auto_block(scale: float) -> int:
    """The `0 = auto` block size in working pixels: 64 source px at `scale`.

    The one definition. The tab's spinner label (`auto (N)`), the kernel, and
    the count-threshold denominator all call this; a second copy is how a
    grid and the band denominated against it end up disagreeing.
    """
    return max(1, round(AUTO_BLOCK_SOURCE_PX * scale))


def resolve_block(block: int, scale: float) -> int:
    """Effective block size in working pixels: explicit, or auto from scale."""
    return block if block > 0 else auto_block(scale)


def grid_shape(height: int, width: int, block: int) -> tuple[int, int]:
    """The `(ny, nx)` block grid for a working frame — ceiling division.

    Partial edge blocks are real blocks (averaged over the pixels they
    actually hold), matching v1's `include_partial=True` extraction path. A
    count threshold's denominator is `ny * nx` from here and nowhere else.
    """
    return -(-height // block), -(-width // block)


class Signal(StrEnum):
    """Which read of the structure tensor leaves the node."""

    #: Blurred `<I_t^2>` — flicker/appearance-change energy. Cheap.
    CHANGE_ENERGY = "change_energy"
    #: Lucas-Kanade speed in px/s. All six products, ~4x the cost.
    FLOW_SPEED = "flow_speed"
    #: Spatial coherency of the block tensor in [0, 1]: does one translation
    #: explain this block's change? All six products, flow_speed's cost tier.
    COHERENCE = "coherence"


@register_filter(
    filter_id="block_signal",
    version="1.0.0",
    summary="Per-block motion signal from the structure tensor of consecutive frames.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),
    # The output is always a block grid: one float32 value per block, GRAY.
    emits=ArraySpec(dtypes=("float32",), channels=(ChannelSpec.GRAY,)),
    cost=CostEstimate(
        # Dominated by the Gaussian blurs. v1's change-only pass measured the
        # products + one blur at ~7% of a full six-component pass; this
        # declaration takes the six-blur tier shared by flow_speed and
        # coherence because a static number cannot branch on a parameter.
        # (Coherence's eigensolves are a few hundred 3x3 symmetric matrices
        # per frame — not the cost.)
        seconds_per_megapixel=0.012,
        # Worst case (flow_speed): the gray frame, the previous frame, six
        # product planes and their blurs reusing storage, plus u/v/speed.
        peak_bytes_per_input_byte=12.0,
    ),
    mode=Mode.STREAMING,
    # The first frame has no previous frame and emits an all-zero grid; one
    # frame of lead-in replaces it with a real measurement.
    warmup_frames=1,
    stateful=True,
    primary_params=("signal", "block"),
)
class BlockSignalParams(ParamsBase):
    """Which signal, on what grid, at what time scale."""

    signal: Signal = Signal.CHANGE_ENERGY
    #: Working pixels per block; 0 means auto (64 source px at `scale`).
    block: int = Field(default=0, ge=0, le=1024)
    #: The upstream rescale factor, used only to resolve an auto block. The
    #: tab writes it from the rescale card; it defaults to 1.0 (no rescale).
    scale: float = Field(default=1.0, ge=0.05, le=1.0)
    #: Source frame rate, used only to express flow_speed in px/s rather than
    #: px/frame. The tab writes it from the video metadata.
    fps: float = Field(default=30.0, gt=0.0)

    def frame_bytes_ratio(self) -> float:
        """One float32 per block against the input frame's pixels.

        Approximate — it assumes float32 single-channel input, which is what
        the normalize step upstream emits. Feeds the storage prediction,
        never a correctness decision.
        """
        return 1.0 / resolve_block(self.block, self.scale) ** 2


@dataclass(slots=True)
class BlockSignalState:
    """The previous preprocessed gray frame. `None` until the first frame."""

    prev: FloatArray | None = None


@stateful_kernel(BlockSignalParams, Backend.CPU, state=BlockSignalState)
def block_signal_cpu(frame: Frame, params: BlockSignalParams, state: BlockSignalState) -> Frame:
    """Measure this frame against the previous one, then remember it.

    The first frame of a run emits an all-zero grid — there is no motion to
    measure across a boundary that has no other side — and `warmup_frames=1`
    tells the planner to feed one lead-in frame so a requested span never
    starts on that zero.

    Raises:
        ValueError: if the frame's shape changes mid-run; one run is one
            geometry, exactly as `background_ema` refuses a reseed.
    """
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
    else:
        out = _block_mean(_flow_speed(prev, gray, params.fps), block, ny, nx)

    return Frame(data=out, index=frame.index, channels=ChannelSpec.GRAY)


def _to_gray(frame: Frame) -> NDArray[np.float32]:
    """The frame as float32 gray, whatever came in.

    v1 converted to gray inside its preprocessor; here the conversion lives
    at the top of extraction so the spatial-prep steps stay layout-agnostic.
    BT.601 weights via cv2, matching `normalize`'s statistics projection.
    """
    data = np.asarray(frame.data, np.float32)
    if frame.channels is ChannelSpec.GRAY:
        return data
    code = cv2.COLOR_BGR2GRAY if frame.channels is ChannelSpec.BGR else cv2.COLOR_RGB2GRAY
    return cast(NDArray[np.float32], cv2.cvtColor(data, code))


def _blur(plane: FloatArray) -> NDArray[np.float32]:
    """One tensor product, spatially windowed. The cast contains cv2's
    `MatLike` return so the solve below stays typed."""
    return cast(NDArray[np.float32], cv2.GaussianBlur(plane, (0, 0), SIGMA))


def _flow_speed(prev: FloatArray, gray: FloatArray, fps: float) -> NDArray[np.float32]:
    """Per-pixel LK speed in px/s from the blurred structure tensor.

    Five products, each blurred with `SIGMA` before the solve — the blur is
    the tensor window, and solving on unblurred products would make every
    pixel its own (rank-deficient) window. (The sixth component, tt, is not
    read by the solve and is not formed.)
    """
    it = gray - prev
    grads = np.gradient(gray)  # d/drow, d/dcol
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
    u = -(yy * xt - xy * yt) * inv
    v = -(xx * yt - xy * xt) * inv
    return (np.hypot(u, v) * fps).astype(np.float32)


def _coherence(
    prev: FloatArray, gray: FloatArray, block: int, ny: int, nx: int
) -> NDArray[np.float32]:
    """Spatial coherency of the block-reduced 3D structure tensor, in [0, 1].

    All six blurred products are block-mean reduced *first* — six numbers per
    block — and the 3x3 symmetric eigensolve runs on the block tensor. The
    order is load-bearing, the mirror of the LK constraint above: a per-pixel
    tensor is near rank-one (one gradient direction), so decomposing before
    reduction reads every pixel as coherent and averaging those verdicts
    destroys exactly the anisotropy being measured. Only aggregation over a
    block lets mixed motion directions raise the small eigenvalues.

    The scalar is Haussecker & Spies' spatial coherency
    `((lam2 - lam3) / (lam2 + lam3))^2` with `lam1 >= lam2 >= lam3`: a single
    translation `(u, v)` explains all change in a block iff every space-time
    gradient is orthogonal to `(u, v, 1)`, i.e. iff the tensor has a null
    direction — `lam3 ~ 0` against a nonzero `lam2`. Opposing or in-place
    motion fills the spectrum and drives it to 0. (The spec's draft formula
    `((lam1 - lam2) / (lam1 + lam2))^2` fails its own translation test — see
    `docs/findings/` on the coherence formula.)

    Blocks with exactly zero temporal change would score a vacuous 1 (the
    t-axis itself is the null direction); they report 0 instead — the same
    honesty as flow_speed's determinant guard.
    """
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
    lam = np.maximum(np.linalg.eigvalsh(tensor), 0.0)  # ascending: lam3, lam2, lam1
    lam3, lam2 = lam[..., 0], lam[..., 1]
    denom = lam2 + lam3
    safe = denom > 0.0
    coh = np.where(safe, ((lam2 - lam3) / np.where(safe, denom, 1.0)) ** 2, 0.0)
    return np.where(tensor[:, :, 2, 2] > 0.0, coh, 0.0).astype(np.float32)


def _block_mean(field: FloatArray, block: int, ny: int, nx: int) -> NDArray[np.float32]:
    """Block-mean with partial edge blocks averaged over their true pixels.

    NaN-pad to the grid, then nanmean per cell — v1's `include_partial=True`
    semantics: an edge block's value is the mean of the pixels it actually
    covers, not diluted against padding.
    """
    h, w = field.shape
    f32 = field.astype(np.float32, copy=False)
    if ny * block == h and nx * block == w:
        return f32.reshape(ny, block, nx, block).mean(axis=(1, 3), dtype=np.float32)
    padded = np.pad(f32, ((0, ny * block - h), (0, nx * block - w)), constant_values=np.nan)
    cells = padded.reshape(ny, block, nx, block).transpose(0, 2, 1, 3)
    return np.nanmean(cells.reshape(ny, nx, block * block), axis=2).astype(np.float32)
