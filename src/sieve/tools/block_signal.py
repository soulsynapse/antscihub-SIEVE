"""Per-block motion signals from the structure tensor of consecutive frames.

The extraction step: each output frame is a small `(ny, nx)` GRAY float32 grid,
one value per block, and the *series* of those frames is what the temporal tools
and the detector consume. Ported from v1
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
  (grooming, flicker) near 0.
* **flow_agreement** (new in SIEVE): the circular resultant of the block's unit
  LK vectors in [0, 1] — of the pixels that resolved a flow, how many moved the
  same way. Free on top of flow_speed's solve: no new product, no new blur, no
  new state. It asks coherence's question of different evidence (the
  above-determinant flow field, not the eigenspectrum) and measurably gets a
  different answer — rank correlation 0.09-0.17 against coherence over the
  reference footage, which falsified the prediction that it would be redundant
  (v2's `docs/findings/2026.07.28-four-free-block-measures-two-survive.md`).

One tool with a `signal` parameter rather than four tools: the four share the
state, the gradient, and the reduction, and switching between them is a
parameter change in place — the same node, the same bands.

**The optical flow is private to this module.** `_lk_flow` and its neighbours
are what a second tool wanting them would have to ask `ops/` for, and that
question is answered by a second consumer arriving, not by this one
(`adr/ops-admission-is-two-tools.md`).

**Block resolution lives in exactly one exported function.** `0 = auto` means
`max(1, round(64 source px x scale))`: the grid is held fixed in *source*
pixels, so turning the rescale knob changes compute cost, not where a
detection localizes. `scale` and `fps` are explicit parameters because the
kernel must stay pure — it cannot ask the graph what the upstream rescale did
or what the container's frame rate is; whatever configures the node writes both
from values it already owns.

Stateful (the previous frame is the state) and `warmup_frames = 1`, which is a
*bounded* warmup: `it = g - gp` reaches one frame back and no further, so two
frames determine every value this tool emits and nothing older than that can
change one. So it is keyed, and the executor re-settles the state over its one
frame when a served range leaves it behind
(`adr/cache-admission-is-bounded-warmup.md`). Until 06.5 it was refused a key for
being stateful, which is the same declaration `background_ema` makes about a
dependence that never ends.

v2 declared a `CostEstimate` and a `frame_bytes_ratio` here; both are cut for
`downsample.py`'s reason — each fed machinery v3 has not built, and a
declaration arrives with its consumer (`adr/declared-means-verified.md`). The
ratio is `1 / resolve_block(...)**2` when the storage readout comes to want it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

import cv2
import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from sieve.core.tool_base import (
    ArraySpec,
    CaptionPart,
    ElementKind,
    ElementNames,
    Emission,
    Mode,
    ParamsBase,
    ParamStereotype,
    WarmupKind,
)
from sieve.core.tool_registry import register_tool
from sieve.core.types import ChannelSpec, Frame, FrameCount, FrameSpan

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

    The one definition. A spinner's label (`auto (N)`), the kernel, and the
    count-threshold denominator all call this; a second copy is how a grid and
    the band denominated against it end up disagreeing.
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
    #: Circular resultant of the block's unit flow vectors in [0, 1]: do the
    #: pixels that moved, move the same way? Free on top of flow_speed.
    FLOW_AGREEMENT = "flow_agreement"


@dataclass(slots=True)
class BlockSignalState:
    """The previous preprocessed gray frame. `None` until the first frame."""

    prev: FloatArray | None = None


def run(params: BlockSignalParams, window: FrameSpan, state: BlockSignalState, /) -> Frame:
    """Measure this frame against the previous one, then remember it.

    The first frame of a run emits an all-zero grid — there is no motion to
    measure across a boundary that has no other side — and `warmup_frames=1`
    tells the planner to feed one lead-in frame so a requested span never
    starts on that zero.

    Raises:
        ValueError: if the frame's shape changes mid-run; one run is one
            geometry, because the state is the previous frame and there is no
            correspondence between two grids of different sizes to carry across.
    """
    frame = window.target
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


@register_tool(
    tool_id="block_signal",
    version="1.0.0",
    summary="Per-block motion signal from the structure tensor of consecutive frames.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),
    # The output is always a block grid: one float32 value per block, GRAY.
    emits=ArraySpec(dtypes=("float32",), channels=(ChannelSpec.GRAY,)),
    # Four measurements of one tensor rather than one measurement computed four
    # ways, which is what makes them four emissions: change energy and coherence
    # answer different questions of the same block and a session that wants both
    # keeps both.
    emissions=(
        Emission(Signal.CHANGE_ENERGY, "signal"),
        Emission(Signal.FLOW_SPEED, "signal"),
        Emission(Signal.COHERENCE, "signal"),
        Emission(Signal.FLOW_AGREEMENT, "signal"),
    ),
    run=run,
    # The tool that redefines what one element is, whatever it was handed —
    # which is why `blocks_in_band` is a name a detection over this node's
    # output may honestly use, and one over its input may not.
    element=ElementKind.BLOCK,
    element_names=ElementNames("block", "blocks"),
    mode=Mode.STREAMING,
    settling_epsilon=0.0,
    # Exact, not settled: the state is the previous frame and nothing older
    # reaches the difference, so two frames decide every output value.
    warmup_kind=WarmupKind.BOUNDED,
    stateful=True,
    state_factory=BlockSignalState,
    primary_params=("signal", "block"),
    caption=(
        CaptionPart(param="signal"),
        CaptionPart(label="block", param="block"),
    ),
    param_value_labels={
        "signal": {
            Signal.CHANGE_ENERGY.value: "change energy (Jtt)",
            Signal.FLOW_SPEED.value: "LK optical flow",
            Signal.COHERENCE.value: "coherence (0-1)",
            Signal.FLOW_AGREEMENT.value: "flow agreement (0-1)",
        }
    },
    # `scale` and `fps` are numbers within declared bounds like any other, and
    # the stereotype says how a value is *populated* rather than who is expected
    # to populate it: a front end that mirrors them from the rescale node and the
    # container writes them through the same param path a spinbox edit takes.
    param_stereotypes={
        "signal": ParamStereotype.ENUM,
        "block": ParamStereotype.SCALAR_RANGE,
        "scale": ParamStereotype.SCALAR_RANGE,
        "fps": ParamStereotype.SCALAR_RANGE,
    },
)
class BlockSignalParams(ParamsBase):
    """Which signal, on what grid, at what time scale."""

    signal: Signal = Signal.CHANGE_ENERGY
    #: Working pixels per block; 0 means auto (64 source px at `scale`).
    block: int = Field(default=0, ge=0, le=1024)
    #: The upstream rescale factor, used only to resolve an auto block. It
    #: defaults to 1.0 (no rescale).
    scale: float = Field(default=1.0, ge=0.05, le=1.0)
    #: Source frame rate, used only to express flow_speed in px/s rather than
    #: px/frame.
    fps: float = Field(default=30.0, gt=0.0)

    @classmethod
    def max_warmup_frames(cls) -> FrameCount:
        """One previous frame is the fixed lead-in for a frame difference."""
        return FrameCount(1)

    def presentation_values(self) -> dict[str, str]:
        shown = f"auto ({resolve_block(0, self.scale)})" if self.block == 0 else str(self.block)
        return {"block": shown}


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


def _lk_flow(
    prev: FloatArray, gray: FloatArray
) -> tuple[NDArray[np.float32], NDArray[np.float32], NDArray[np.bool_]]:
    """Per-pixel LK flow `(u, v)` and the mask of pixels that resolved it.

    Five products, each blurred with `SIGMA` before the solve — the blur is
    the tensor window, and solving on unblurred products would make every
    pixel its own (rank-deficient) window. (The sixth component, tt, is not
    read by the solve and is not formed.)

    The mask is returned rather than re-derived by each caller because it is
    the same honesty guard twice: `flow_speed` reports zero where it is false,
    `flow_agreement` averages only where it is true, and two copies of the
    determinant test are two things that can disagree about which pixels were
    measured at all.
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
    u = (-(yy * xt - xy * yt) * inv).astype(np.float32)
    v = (-(xx * yt - xy * xt) * inv).astype(np.float32)
    return u, v, safe


def _flow_speed(prev: FloatArray, gray: FloatArray, fps: float) -> NDArray[np.float32]:
    """Per-pixel LK speed in px/s. Zero exactly where the solve was degenerate."""
    u, v, _ = _lk_flow(prev, gray)
    return (np.hypot(u, v) * fps).astype(np.float32)


def _flow_agreement(
    prev: FloatArray, gray: FloatArray, block: int, ny: int, nx: int
) -> NDArray[np.float32]:
    """Resultant length of the block's unit flow vectors, in [0, 1].

    Direction is a circular quantity, so the block reduction is a *circular*
    mean: each measurable pixel contributes a unit vector, and the length of
    their mean is how much they agree. Averaging `atan2` instead would make
    two pixels moving in exactly opposite directions average to a direction
    nobody moved in; averaging unit vectors makes them cancel, which is the
    answer.

    The mean runs over the above-determinant pixels only — dividing the
    summed unit vectors by the *count of measured pixels*, not by the block's
    pixel count. That is what makes this differently robust from `coherence`
    rather than a restatement of it: the eigensolve sees all change in the
    block, this sees only the change that resolved into a flow vector. A
    block half of which is featureless floor then reports the agreement of
    the half that moved, instead of reporting half of it.

    A block with no measurable pixel reports 0 — the same position
    `flow_speed` takes under the aperture problem, and it means "nothing
    measured here", not "these pixels disagreed".
    """
    u, v, safe = _lk_flow(prev, gray)
    speed = np.hypot(u, v)
    moving = safe & (speed > 0.0)
    scale = np.where(moving, 1.0 / np.where(moving, speed, 1.0), 0.0)
    sum_x = _block_mean((u * scale).astype(np.float32), block, ny, nx)
    sum_y = _block_mean((v * scale).astype(np.float32), block, ny, nx)
    share = _block_mean(moving.astype(np.float32), block, ny, nx)
    ok = share > 0.0
    inv_share = np.where(ok, 1.0 / np.where(ok, share, 1.0), 0.0)
    return np.minimum(np.hypot(sum_x * inv_share, sum_y * inv_share), 1.0).astype(np.float32)


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
    motion fills the spectrum and drives it to 0. (The draft formula
    `((lam1 - lam2) / (lam1 + lam2))^2` fails its own translation test, which is
    what v2's coherence finding records.)

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

    The full-cell core reduces as a reshape view. Ceiling division can make
    only the final row and final column short, so the partial edge is three
    slabs rather than a padded plane. If the input field itself carries NaN,
    fall back to the old `nanmean` route so NaN-skipping semantics remain.
    """
    h, w = field.shape
    f32 = field.astype(np.float32, copy=False)
    out = np.empty((ny, nx), np.float32)
    full_y, full_x = h // block, w // block
    rem_y, rem_x = h - full_y * block, w - full_x * block
    if full_y and full_x:
        core = f32[: full_y * block, : full_x * block]
        out[:full_y, :full_x] = core.reshape(full_y, block, full_x, block).mean(
            axis=(1, 3), dtype=np.float32
        )
    if ny > full_y and full_x:
        out[full_y, :full_x] = (
            f32[full_y * block :, : full_x * block]
            .reshape(rem_y, full_x, block)
            .mean(axis=(0, 2), dtype=np.float32)
        )
    if nx > full_x and full_y:
        out[:full_y, full_x] = (
            f32[: full_y * block, full_x * block :]
            .reshape(full_y, block, rem_x)
            .mean(axis=(1, 2), dtype=np.float32)
        )
    if ny > full_y and nx > full_x:
        out[full_y, full_x] = f32[full_y * block :, full_x * block :].mean(dtype=np.float32)
    if np.isnan(out).any():
        return _block_mean_nan_padded(f32, block, ny, nx)
    return out


def _block_mean_nan_padded(
    field: NDArray[np.float32], block: int, ny: int, nx: int
) -> NDArray[np.float32]:
    padded = np.pad(
        field,
        ((0, ny * block - field.shape[0]), (0, nx * block - field.shape[1])),
        constant_values=np.nan,
    )
    cells = padded.reshape(ny, block, nx, block).transpose(0, 2, 1, 3)
    return np.nanmean(cells.reshape(ny, nx, block * block), axis=2).astype(np.float32)
