"""The kernel's own claims: that it remembers, and that its warmup is honest.

Ported from v2's file of the same name, whose framing carries. The claims about
*where* state lives — one model per run, never shared, never cached — belong to
the executor and the registry and are tested in `test_stateful_execution.py`.
The claim that a refined warmup is charged instead of a bound belongs to the
contract and is tested in `test_tool_contract.py`. What is left here is what only
this tool can get wrong: the recursion, the declared settle time, and the
narrowing on the way back out.

What is new is the parity half, on 03.7's mechanism. One golden per `emit`,
because the two are two code paths that share only the model: the background is
the accumulator handed out, while the foreground is the difference taken against
it after the update. Both goldens are cut from uint8 footage, which is also what
pins `_narrow`'s rounding — the truncating version differs from this one by a
level on about half the pixels, and no inequality in this file would notice.

The last case is not about the kernel and is here anyway.
`adr/cache-admission-is-bounded-warmup.md` refuses this tool a key and leaves
one revival open with a measurement attached — admitting it on a *measured*
epsilon, if a residual under the declared threshold turns out not to reach an
answer anyone reads. That measurement is the two runs this file already knows
how to build, carried into `detect`, because the gate is the shortest thing a
residual can be shown to flip and there is nowhere nearer to look. Its numbers
live in `docs/findings/2026.08.09-a-sub-epsilon-residual-flips-a-detection.md`.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import pytest
from pydantic import ValidationError

from sieve.core.tool_base import node_warmup_frames
from sieve.core.types import ChannelSpec, Frame, FrameCount, FrameSpan
from sieve.tools.background_ema import (
    MIN_ALPHA,
    SETTLED_EPSILON,
    BackgroundEmaParams,
    BackgroundState,
    Emit,
    settle_frames,
)
from sieve.tools.background_ema import run as background_ema_run
from sieve.tools.detect import (
    DetectParams,
    band_indices,
    default_freqs,
    gate_series,
    inband_count,
    morlet_band_power,
    windowed_mean,
)

#: The shipped spec. Read through a narrowing helper rather than asserted at
#: module scope, because `__tool_spec__` is `ToolSpec | None` and a bare
#: module-level assert does not narrow it inside a function body.
SPEC = BackgroundEmaParams.spec()

WIDTH, HEIGHT = 12, 9

DEFAULTS = BackgroundEmaParams()
SETTLED = BackgroundEmaParams(emit=Emit.BACKGROUND)

#: The one naming scheme the command below writes and this file reads, on
#: `test_block_signal.py`'s mechanism: named rather than spelled twice, so the
#: checked-in set can be compared against the command instead of against a second
#: copy of the scheme.
GOLDEN_PREFIX = "background_ema_24x9x12_a025_"

#: The `alpha` every golden was cut at. A golden regenerated under a different
#: one would still load and still compare, so the number lives in one place the
#: command and the parity case both read.
GOLDEN_ALPHA = 0.25

#: What produced this file's goldens, run from the repo root, on
#: `test_rescale_normalize.py`'s mechanism and for its reason: `git diff --quiet`
#: is what makes the arrays a statement about v2's `main` rather than about
#: whatever sits in the sibling worktree, and `--project` enters v2's environment
#: because reproducing the array means reproducing v2's package.
#:
#: The series is `golden_series()` below, spelled out rather than imported — the
#: regenerating process has v2's `sieve` on its path and not this one's, and a
#: fixture the command builds differently from the test is a golden that pins a
#: series nothing here ever produces.
REGENERATE = (
    "git -C ../antscihub-SIEVE-v2 diff --quiet main -- "
    "src/sieve/filters/background_ema.py src/sieve/core/types.py && "
    'uv run --project ../antscihub-SIEVE-v2 python -c "'
    "import numpy as np; "
    "from sieve.core.types import ChannelSpec, Frame; "
    "from sieve.filters.background_ema import BackgroundEmaParams, BackgroundState, Emit, "
    "background_ema_cpu; "
    "s = np.random.default_rng(5).integers(0, 256, (24, 9, 12), dtype=np.uint8); "
    "s[12:, 2:5, 3:7] = 250; "
    "last = lambda p: [background_ema_cpu(Frame(data=d, index=i, channels=ChannelSpec.GRAY), "
    "p, st).data for st in [BackgroundState()] for i, d in enumerate(s)][-1]; "
    f"[np.save('tests/goldens/{GOLDEN_PREFIX}' + e.value + '.npy', "
    f'last(BackgroundEmaParams(alpha={GOLDEN_ALPHA}, emit=e))) for e in Emit]"'
)

GOLDENS = Path(__file__).resolve().parents[1] / "goldens"

#: Frames the re-settled run starts at. The cold run starts at zero, so the two
#: carry different origins into the span they meet on — a re-settled run that
#: began where the cold one did would be the same run, and the case would be
#: measuring nothing.
EPSILON_ENTRY = 40

#: Frames the two runs are compared over, past the re-settled one's warmup.
#: Enough that a detection window has somewhere to sit away from both edges.
EPSILON_SPAN_FRAMES = 80

#: Where a served entry would be handed back: the frame the re-settled run has
#: just finished `warmup_frames` at, which is the entry point ADR 17's rule
#: describes for the tools it *does* admit.
EPSILON_SPAN_START = EPSILON_ENTRY + SPEC.warmup_frames.frames

#: What the residual is carried into, and every value is placed on the footage
#: below rather than carried from anywhere. The rate is the reference fixture's.
#: The band's low edge is 5 Hz because the transform's reach is charged at it and
#: the wide-open default would put 164 frames either side of every target
#: (`tools/detect.wavelet_edge_frames`); the patch blinks inside it. The value
#: floor and the window are where the in-band count runs over a range instead of
#: saturating, which is the only state in which a threshold can be placed at all.
EPSILON_FPS = 20.0
EPSILON_FREQ_LO = 5.0
EPSILON_VALUE_FLOOR = 500.0
EPSILON_WINDOW_FRAMES = 15


def kernel(frame: Frame, params: BackgroundEmaParams, state: BackgroundState) -> Frame:
    """One frame through the tool, in v2's argument order for its ported cases."""
    return background_ema_run(params, FrameSpan((frame,)), state)


def flat(value: float, index: int = 0, dtype: npt.DTypeLike = np.uint8) -> Frame:
    """A frame of one intensity, so the model is a single number to reason about."""
    data: npt.NDArray[Any] = np.full((HEIGHT, WIDTH), value, dtype=dtype)
    return Frame(data=data, index=index, channels=ChannelSpec.GRAY)


def drive(state: BackgroundState, level: float, count: int, params: BackgroundEmaParams) -> Frame:
    """Feed `count` frames of one level and hand back the last output."""
    produced = kernel(flat(level, 0), params, state)
    for index in range(1, count):
        produced = kernel(flat(level, index), params, state)
    return produced


def golden_series() -> npt.NDArray[np.uint8]:
    """The series both goldens were cut from, and the one this file replays.

    Noise the model has to average down, then a bright patch introduced halfway
    that it is still catching up to at the last frame — which is the only state
    in which the two emits are both non-trivial: a model that had converged
    would emit a foreground of quantization noise, and a golden of that would
    pass for any `alpha` at all.
    """
    series = np.random.default_rng(5).integers(0, 256, (24, HEIGHT, WIDTH), dtype=np.uint8)
    series[12:, 2:5, 3:7] = 250
    return series


def epsilon_footage() -> npt.NDArray[np.float32]:
    """Noise with a patch blinking inside `detect`'s band, long enough for both.

    float32 rather than the uint8 an ordinary chain carries, and that choice is
    about the *premise* rather than the answer: the residual is a fraction of a
    level here, so a bound stated against a uint8 range would sit a few percent
    from what the run measures and go red on an unrelated edit to this fixture.
    The narrowing does not rescue the answer — the uint8 form of this same run
    is an amendment in the finding, at a whole level of residual and a larger
    shift in the count than this one produces.
    """
    frames = EPSILON_SPAN_START + EPSILON_SPAN_FRAMES
    rng = np.random.default_rng(11)
    footage = rng.integers(40, 90, size=(frames, HEIGHT, WIDTH)).astype(np.float32)
    phase = 2.0 * np.pi * 6.0 * np.arange(frames) / EPSILON_FPS
    footage[:, 2:6, 3:8] += (60.0 * (0.5 + 0.5 * np.sin(phase)))[:, None, None]
    return footage


def epsilon_foreground(footage: npt.NDArray[np.float32], start: int) -> npt.NDArray[np.float32]:
    """One run's foreground over the span, as the `(frames, elements)` `detect` reads.

    `start` is where the run's model was seeded, which is the only thing that
    differs between the two runs this file compares — same footage, same `alpha`,
    same span, and an origin the answer never quite loses.
    """
    params = BackgroundEmaParams(alpha=MIN_ALPHA, emit=Emit.FOREGROUND)
    state = BackgroundState()
    rows = []
    for index in range(start, len(footage)):
        frame = Frame(data=footage[index], index=index, channels=ChannelSpec.GRAY)
        produced = kernel(frame, params, state)
        if index >= EPSILON_SPAN_START:
            rows.append(np.asarray(produced.data, np.float32).reshape(-1))
    return np.stack(rows)


def epsilon_counts(series: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
    """The windowed in-band count `detect` thresholds, for one run's series.

    `detect` emits the gate and not the number the gate is a comparison of, so
    the threshold cannot be *placed* between two runs without re-deriving it.
    This is that derivation, off the same public pieces `detect._chain` composes.
    It is not a second answer that could drift unnoticed: the case below places a
    threshold from these numbers and then asks `gate_series` — the tool's own
    composition — what it decides, so a spelling that had drifted apart from the
    chain would show up as a gate that did not flip.
    """
    freqs = default_freqs(EPSILON_FPS)
    low, high = band_indices(freqs, EPSILON_FREQ_LO, math.inf)
    power = morlet_band_power(series, EPSILON_FPS, freqs, low, high, workers=1)
    counted = inband_count(power, EPSILON_VALUE_FLOOR, math.inf)
    return windowed_mean(counted, EPSILON_WINDOW_FRAMES, True)


def test_the_state_is_what_makes_the_output_differ_for_one_frame() -> None:
    """The same frame through a cold state and a warm one is two answers.

    A stateless kernel cannot produce two answers for one input, so if these two
    agree, nothing is being remembered and the 90 frames of lead-in the spec asks
    for are being decoded for nothing.
    """
    cold = BackgroundState()
    warm = BackgroundState()
    drive(warm, level=200, count=30, params=DEFAULTS)

    from_cold = kernel(flat(100, index=30), DEFAULTS, cold)
    from_warm = kernel(flat(100, index=30), DEFAULTS, warm)

    # Cold: the model is seeded to this very frame, so there is nothing to
    # differ from. Warm: the model is still near 200, so 100 is foreground.
    assert not from_cold.data.any()
    assert from_warm.data.mean() > 50


def test_the_model_converges_to_within_the_declared_epsilon_by_the_declared_frame() -> None:
    """`warmup_frames=90` is a claim about convergence, and this is that claim.

    An EMA's warmup is nominally infinite, so the spec declares a
    settled-to-within-epsilon number and the epsilon it is judged against.
    Nothing else in the repo checks that the number and the epsilon describe the
    same tool — the plan's warmup arithmetic would be equally happy with a
    declaration of 3 or 3000.

    Two seeds two hundred levels apart, then identical footage: after
    `warmup_frames` the two models must agree to within `epsilon` of the gap
    they started with, because that is what the residual weight on the seed
    means.
    """
    gap = 200.0
    epsilon = SPEC.settling_epsilon
    assert epsilon == SETTLED_EPSILON

    def divergence_after(frames: int) -> float:
        """How far apart two models seeded `gap` apart are after `frames` more."""
        low, high = BackgroundState(), BackgroundState()
        from_low = kernel(flat(0), SETTLED, low)
        from_high = kernel(flat(gap), SETTLED, high)
        for index in range(1, frames + 1):
            from_low = kernel(flat(128, index), SETTLED, low)
            from_high = kernel(flat(128, index), SETTLED, high)
        return abs(float(from_low.data.mean()) - float(from_high.data.mean()))

    assert epsilon is not None
    assert divergence_after(SPEC.warmup_frames.frames) <= gap * epsilon

    # And the declaration is not slack by an order of magnitude: a tenth of the
    # frames must *not* be enough, or `warmup_frames` would be paying for
    # lead-in nobody needs.
    assert divergence_after(SPEC.warmup_frames.frames // 10) > gap * epsilon


def test_a_sub_epsilon_difference_reaches_a_detection() -> None:
    """The measurement ADR 17 left owed, and it closes the option it was owed for.

    The ADR refuses this tool a key and names one way back in: "admitting
    `background_ema` and `temporal_baseline` on a measured epsilon. Whether a
    difference below the declared threshold survives into a detection flip is
    unmeasured, and nothing here admits them." This is that measurement, built
    as the admission itself would be — a cold run from the first frame of the
    footage, and a run entering at the span having re-settled over exactly
    `warmup_frames` first, which is what a served entry hands back.

    The two agree to within the declared epsilon, which is the premise and is
    asserted rather than assumed. They are not equal, which is what an epsilon
    warmup means and is asserted too. And the residual reaches the gate: the
    windowed in-band count differs, so a threshold placed between the two
    fires for one run and not the other.

    A threshold placed between them is where a tuned threshold *is*. The gesture
    the product is built around is dragging a handle until the detection just
    appears, so the band a session ends up in is the band where a residual this
    size decides the answer — which is why this is a measurement about the
    product and not an adversarial construction. The size of that band relative
    to the count's own range is the number that says how often it matters, and
    it is in the finding.
    """
    footage = epsilon_footage()
    cold = epsilon_foreground(footage, 0)
    resettled = epsilon_foreground(footage, EPSILON_SPAN_START - SPEC.warmup_frames.frames)

    epsilon = SPEC.settling_epsilon
    assert epsilon is not None
    residual = float(np.abs(cold - resettled).max())
    assert 0.0 < residual <= epsilon * float(footage.max() - footage.min())

    counted = [epsilon_counts(series) for series in (cold, resettled)]
    frame = int(np.argmax(np.abs(counted[0] - counted[1])))
    assert counted[0][frame] != counted[1][frame]

    between = (float(counted[0][frame]) + float(counted[1][frame])) / 2.0
    params = DetectParams(
        freq_band=(EPSILON_FREQ_LO, math.inf),
        value_band=(EPSILON_VALUE_FLOOR, math.inf),
        count_frac=(between / cold.shape[1], math.inf),
        window_frames=EPSILON_WINDOW_FRAMES,
        centered=True,
        fps=EPSILON_FPS,
    )
    gates = [gate_series(series, params) for series in (cold, resettled)]

    assert gates[0] is not None and gates[1] is not None
    assert bool(gates[0][frame]) != bool(gates[1][frame])


def test_the_declared_warmup_is_the_worst_case_over_the_legal_alpha_range() -> None:
    """90 is `settle_frames(MIN_ALPHA)`, and no legal `alpha` needs more.

    The failure this closes is a lower bound on `alpha` being relaxed later —
    which is a one-character edit to a `Field` — without the warmup bound moving
    with it. That would leave the spec declaring a lead-in shorter than the tool
    needs, which is the silent direction: the preview renders, the model has not
    settled, and the tuning done against it is wrong rather than absent.
    """
    lower_bound = MIN_ALPHA
    assert BackgroundEmaParams(alpha=lower_bound).alpha == lower_bound
    with pytest.raises(ValidationError):
        BackgroundEmaParams(alpha=lower_bound / 2)

    assert SPEC.warmup_frames == FrameCount(settle_frames(lower_bound))
    assert settle_frames(1.0) == 1
    # Monotone: a slower model needs more warmup, which is why the bound is the
    # worst case rather than the default.
    assert settle_frames(0.5) < settle_frames(0.1) < settle_frames(lower_bound)


def test_a_fast_model_is_charged_its_own_warmup_rather_than_the_bound() -> None:
    """The bound is the worst case; a run pays for the `alpha` it configured.

    Without the refinement, `alpha = 0.5` decodes 90 frames of lead-in to settle
    a model that needs 7 — which is what v2 did, and what
    `ParamsBase.warmup_frames` exists to stop. This is the assertion that says
    so: it fails if the override is dropped and the spec's constant silently
    takes over again.
    """
    step = (SPEC, BackgroundEmaParams(alpha=0.5))

    assert node_warmup_frames(step) == FrameCount(settle_frames(0.5)) == FrameCount(7)
    assert node_warmup_frames((SPEC, BackgroundEmaParams())) == SPEC.warmup_frames


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16, np.float32, np.float64])
def test_the_output_dtype_is_the_inputs_however_wide_the_accumulator(
    dtype: npt.DTypeLike,
) -> None:
    """The frame that comes out is the dtype the graph declared it would be.

    The model is float internally whatever arrived, so without the narrowing
    every downstream node would see float64 where the edge check promised
    uint8 — and `ArraySpec.admits` would have been satisfied by a declaration
    the kernel did not keep.
    """
    produced = drive(BackgroundState(), level=50, count=3, params=SETTLED)
    assert produced.data.dtype == np.dtype(np.uint8)

    widened = kernel(flat(50, 3, dtype), DEFAULTS, BackgroundState())
    assert widened.data.dtype == np.dtype(dtype)


def test_an_emitted_frame_is_not_a_view_of_the_state() -> None:
    """The next frame must not rewrite the last one under its holder.

    Both emit paths hand back one of the state's three reused buffers, and both
    would be correct for exactly one frame if returned as a view. The symptom is
    remote from the cause: a result the GUI is still painting changes mid-paint,
    and a store entry stops matching the key it was written under. Float32 is the
    dtype where a careless `astype(copy=False)` is a no-op and so is the one that
    catches it.
    """
    for emit in Emit:
        state = BackgroundState()
        params = BackgroundEmaParams(alpha=0.5, emit=emit)
        first = kernel(flat(10, 0, np.float32), params, state)
        held = first.data.copy()
        kernel(flat(250, 1, np.float32), params, state)

        assert np.array_equal(first.data, held), f"{emit} handed back a view of the state"


def test_a_mid_run_shape_change_is_refused_rather_than_reseeded() -> None:
    """A silent reseed would restart the 90-frame warmup with nobody told."""
    state = BackgroundState()
    kernel(flat(10), DEFAULTS, state)

    other = Frame(data=np.zeros((4, 4), np.uint8), index=1, channels=ChannelSpec.GRAY)
    with pytest.raises(ValueError, match="one run is one geometry"):
        kernel(other, DEFAULTS, state)


@pytest.mark.parametrize("emit", list(Emit))
def test_each_emit_reproduces_the_v2_golden(emit: Emit) -> None:
    """v3's kernel reproduces v2's array exactly, on both outputs.

    Equality rather than a tolerance, as everywhere else in the Phase-4 gate.
    The last frame of `golden_series()` is the one worth pinning: the model is
    twelve frames into chasing the bright patch, so neither emit is a converged
    array that any nearby `alpha` would also produce.
    """
    golden = np.load(GOLDENS / f"{GOLDEN_PREFIX}{emit.value}.npy")
    params = BackgroundEmaParams(alpha=GOLDEN_ALPHA, emit=emit)
    state = BackgroundState()

    for index, plane in enumerate(golden_series()):
        produced = kernel(
            Frame(data=plane, index=index, channels=ChannelSpec.GRAY), params, state
        ).data

    assert produced.dtype == golden.dtype
    assert np.array_equal(produced, golden)


def test_the_goldens_are_two_different_arrays() -> None:
    """Two emits that happened to be one array would pass parity for nothing.

    They are different quantities — the background is in the footage's units and
    the foreground is a distance in them — so an implementation that emitted the
    model down both branches would satisfy every inequality above and fail only
    here.
    """
    arrays = [np.load(GOLDENS / f"{GOLDEN_PREFIX}{emit.value}.npy") for emit in Emit]

    assert not np.array_equal(arrays[0], arrays[1])


def test_the_regeneration_command_names_every_golden() -> None:
    """A golden the recorded command does not write is a golden nobody can redo.

    The command composes its names from `GOLDEN_PREFIX` and the emit values, so
    the check is that the scheme is the one recorded and that the checked-in set
    is exactly what it produces — no golden outside it, and none missing.
    """
    assert GOLDEN_PREFIX in REGENERATE
    assert "for e in Emit" in REGENERATE

    written = sorted(path.name for path in GOLDENS.glob(f"{GOLDEN_PREFIX}*.npy"))
    assert written == sorted(f"{GOLDEN_PREFIX}{emit.value}.npy" for emit in Emit)
    assert f"alpha={GOLDEN_ALPHA}" in REGENERATE
