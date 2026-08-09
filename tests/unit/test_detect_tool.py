"""What only the detect tool can get wrong: the second side of its window.

The transform's own claims are `test_wavelet.py`'s and the chain's are
`test_detection.py`'s — both ported from v2, both pointed at this module's new
home. What is left here is the part v2 could not have a test for, because v2
could not run this tool: that the window is *centred*, that both halves of it
are declared, and that a run through the one execution path reproduces the
whole-record result the detector was tuned against.

The parity target is v2's `detect/` package output and never its trailing
kernel (`adr/detector-is-a-node.md`, PLAN.md Phase 4). That kernel is the shape
the two-sided window replaced, so a golden cut from it would certify the defect
rather than the tool — which is why `REGENERATE` names the package entry point
and why `test_the_trailing_shape_is_a_different_answer` exists at all: it is the
one case that fails if this tool quietly runs the shape v2 shipped.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest

from sieve.core.pipeline_model import Node, Pipeline, SourceSpan
from sieve.core.tool_base import (
    DisplaySurface,
    ParamStereotype,
    node_lookahead_frames,
    node_warmup_frames,
)
from sieve.core.tool_registry import REGISTRY
from sieve.core.types import ChannelSpec, Frame, FrameCount, FrameSpan
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import execute
from sieve.pipeline.plan import ExecutionPlan
from sieve.tools.detect import (
    MAX_FPS,
    MAX_LOOKAHEAD_FRAMES,
    MAX_WARMUP_FRAMES,
    MAX_WINDOW_FRAMES,
    DetectParams,
    band_indices,
    default_freqs,
    detect_gate,
    gate_series,
    inband_count,
    morlet_band_power,
    morlet_power,
    morlet_power_profile,
    wavelet_edge_frames,
    windowed_mean,
)
from sieve.tools.detect import display as detect_display
from sieve.tools.detect import run as detect_run

SPEC = DetectParams.spec()

FPS = 30.0

#: The golden series' geometry: 256 frames of 12 blocks. Long enough that the
#: event sits clear of both record edges by more than the transform's reach,
#: which is what makes the interior comparison below a statement about the
#: window rather than about the record's ends.
FRAMES, BLOCKS = 256, 12

#: The event: five of the twelve blocks oscillating at 6 Hz for 80 frames.
EVENT_FRAMES = (90, 170)
EVENT_BLOCKS = (3, 8)
EVENT_HZ = 6.0
EVENT_AMPLITUDE = 3.0

#: The one naming scheme `REGENERATE` writes and this file reads, on
#: `test_motion_history.py`'s mechanism: named rather than spelled twice, so the
#: checked-in set can be compared against the command instead of against a
#: second copy of the scheme.
GOLDEN_PREFIX = "detect_256x12_f4to8_d15_"

#: The four arrays v2's package returns that this tool still computes. Its
#: `band_rows` is the snapped bank span a title renders and its `intervals` are
#: rows rather than frames (Phase 5), so neither is an array to pin here.
GOLDEN_NAMES = ("band_power", "count", "windowed", "gate")

GOLDENS = Path(__file__).resolve().parents[1] / "goldens"


def golden_params() -> DetectParams:
    """The configuration every golden was cut at, in v3's spelling.

    The band is 4–8 Hz rather than the wide-open default for one reason worth
    stating: the transform's reach is charged at the band's *lowest* frequency,
    so a band reaching to 0.5 Hz would put 247 frames of window either side of
    every target and make the executor case below a benchmark. At 4 Hz it is 29,
    and the claim under test is unchanged.
    """
    return DetectParams(
        freq_band=(4.0, 8.0),
        value_band=(60.0, math.inf),
        count_frac=(0.25, math.inf),
        window_frames=15,
        centered=True,
        fps=FPS,
    )


#: What produced this file's goldens, run from the repo root, on
#: `test_motion_history.py`'s mechanism and for its reason: `git diff --quiet` is
#: what makes the arrays a statement about v2's `main` rather than about whatever
#: sits in the sibling worktree, and `--project` enters v2's environment because
#: reproducing the array means reproducing v2's package.
#:
#: `from sieve.detect import detect` is the entry point on purpose and is the
#: whole point of the command. v2 also shipped a runnable `filters/detect.py`
#: whose window trailed; a golden cut from that one would pin the shape this tool
#: replaced.
#:
#: The series is `golden_series()` below, spelled out rather than imported — the
#: regenerating process has v2's `sieve` on its path and not this one's, and a
#: fixture the command builds differently from the test is a golden that pins a
#: series nothing here ever produces.
REGENERATE = (
    "git -C ../antscihub-SIEVE-v2 diff --quiet main -- "
    "src/sieve/detect src/sieve/core/ops src/sieve/core/pipeline_model.py && "
    'uv run --project ../antscihub-SIEVE-v2 python -c "'
    "import numpy as np; "
    "from sieve.core.pipeline_model import DetectorSettings; "
    "from sieve.detect import detect; "
    "s = np.random.default_rng(19).normal(0.0, 1.0, (256, 12)).astype(np.float32); "
    "t = np.arange(256) / 30.0; "
    "s[90:170, 3:8] += (3.0 * np.sin(2 * np.pi * 6.0 * t[90:170])).astype(np.float32)[:, None]; "
    "u = detect(s, 30.0, DetectorSettings(freq_band=(4.0, 8.0), value_band=(60.0, np.inf), "
    "count_frac=(0.25, np.inf), window_frames=15, centered=True), workers=1); "
    f"[np.save('tests/goldens/{GOLDEN_PREFIX}' + n + '.npy', getattr(u, n)) "
    "for n in ('band_power', 'count', 'windowed', 'gate')]"
    '"'
)


def golden_series() -> npt.NDArray[np.float32]:
    """The series every golden was cut from, and the one this file replays.

    Noise the transform sees as broadband, plus a narrow-band event on five of
    twelve blocks — enough to put the in-band count over a quarter of the grid
    while it runs and nowhere near it otherwise. The nearest block power to the
    value band's edge is 0.19 out of 60, so the count series is a statement about
    the transform rather than about a threshold coin-flip.
    """
    series = np.random.default_rng(19).normal(0.0, 1.0, (FRAMES, BLOCKS)).astype(np.float32)
    t = np.arange(FRAMES) / FPS
    lo, hi = EVENT_FRAMES
    event = (EVENT_AMPLITUDE * np.sin(2.0 * np.pi * EVENT_HZ * t[lo:hi])).astype(np.float32)
    series[lo:hi, EVENT_BLOCKS[0] : EVENT_BLOCKS[1]] += event[:, None]
    return series


def whole_record(params: DetectParams) -> dict[str, np.ndarray]:
    """The chain over the whole series, one array per name the goldens carry."""
    series = golden_series()
    freqs = default_freqs(params.fps)
    i, j = band_indices(freqs, params.freq_band[0], params.freq_band[1])
    power = morlet_band_power(series, params.fps, freqs, i, j, workers=1)
    count = inband_count(power, params.value_band[0], params.value_band[1])
    windowed = windowed_mean(count, params.window_frames, params.centered)
    assert params.count_frac is not None
    lo = params.count_frac[0] * power.shape[1]
    return {
        "band_power": power,
        "count": count,
        "windowed": windowed,
        "gate": detect_gate(windowed, lo, params.count_frac[1]),
    }


class BlockSource:
    """The golden series as frames: one `(1, BLOCKS)` grid per frame.

    A shape the tool's `accepts` admits and `run` flattens, so the executor case
    below feeds it exactly the series the whole-record derivation reads.
    """

    def __init__(self) -> None:
        self.series = golden_series()

    def read(self, index: int) -> Frame:
        return Frame(
            data=self.series[index][None, :],
            index=index,
            channels=ChannelSpec.GRAY,
        )


def span_for(params: DetectParams, target: int) -> FrameSpan:
    """The window the executor would hand `run` when answering for `target`.

    Including the lookahead the executor puts on the span, without which this
    would be a window that reaches ahead and does not say so — a shape the loop
    never builds, and one that would move where `run` reads its answer.
    """
    source = BlockSource()
    warmup = params.warmup_frames().frames
    lookahead = params.lookahead_frames()
    return FrameSpan(
        tuple(
            source.read(index) for index in range(target - warmup, target + lookahead.frames + 1)
        ),
        lookahead=lookahead,
    )


def test_both_halves_of_the_window_are_declared() -> None:
    """A centred window of `2k+1` is `k` of lead-in and `k` of read-ahead.

    The band is high enough that the transform's reach is the smaller of the two
    numbers, which is the only configuration in which this asserts anything about
    the *detection* window at all: at the default band the transform's reach is
    247 frames and would swallow either answer.
    """
    params = DetectParams(freq_band=(10.0, 13.0), window_frames=101, fps=FPS)
    edge = wavelet_edge_frames(FPS, (10.0, 13.0))

    assert edge < 50
    assert params.warmup_frames() == FrameCount(50)
    assert params.lookahead_frames() == FrameCount(50)

    trailing = params.model_copy(update={"centered": False})
    assert trailing.warmup_frames() == FrameCount(100)
    # The whole window is behind the frame now, so the only thing left to read
    # ahead for is the transform — which still reaches forward, because it always
    # did and v2 charged it on one side only.
    assert trailing.lookahead_frames() == FrameCount(edge)


def test_the_transform_reaches_further_than_the_window_at_the_default_band() -> None:
    """The declaration is the wider of two claims, not the window's alone.

    A band reaching to 0.5 Hz needs 247 frames either side at 30 fps against the
    default window's 15 and 14. A tool that declared only the detection window
    would run its transform against a padded edge and emit a value that changes
    when more of the record arrives — the failure the second frontier was for.
    """
    params = DetectParams(fps=FPS)
    edge = wavelet_edge_frames(FPS, (0.0, math.inf))

    assert edge == 247
    assert params.warmup_frames() == FrameCount(edge)
    assert params.lookahead_frames() == FrameCount(edge)


def test_the_bounds_are_reached_only_at_the_corner_and_every_run_refines_them() -> None:
    """Both bounds are the worst case, and both are worth refining.

    Two directions, as in every other tool's version of this: a refinement above
    the bound is refused at run time by `node_warmup_frames`, and a bound that is
    not the worst case is a decode range and an emission delay a configuration
    can silently exceed. The corner is a band reaching to 0.5 Hz at 240 fps,
    where the transform's reach is 1972 frames and dwarfs even a 600-frame
    window.
    """
    corner = DetectParams(window_frames=MAX_WINDOW_FRAMES, fps=MAX_FPS)

    assert corner.warmup_frames() == SPEC.warmup_frames == FrameCount(MAX_WARMUP_FRAMES)
    assert corner.lookahead_frames() == SPEC.lookahead_frames == FrameCount(MAX_LOOKAHEAD_FRAMES)

    params = golden_params()
    assert node_warmup_frames((SPEC, params)) == FrameCount(29)
    assert node_lookahead_frames((SPEC, params)) == FrameCount(29)
    assert params.warmup_frames() * 60 < SPEC.warmup_frames


def test_the_three_bands_declare_a_band_and_not_a_span() -> None:
    """`SPAN` is frames or time, and none of these three is either.

    `freq_band` is in Hz, `value_band` is in the incoming signal's own units and
    `count_frac` is a fraction of the frame's elements. As controls the two
    stereotypes are indistinguishable — a lo/hi pair, two handles, dragged — and
    as handoff surfaces they share nothing, which is why declaring `freq_band` a
    `SPAN` tells Phase 7's generator to put frequency handles on the scrubber.
    The last assertion is the one that stays true after a fourth band: no
    parameter of this tool belongs on the timeline at all.
    """
    stereotypes = SPEC.param_stereotypes

    assert stereotypes["freq_band"] is ParamStereotype.BAND
    assert stereotypes["value_band"] is ParamStereotype.BAND
    assert stereotypes["count_frac"] is ParamStereotype.BAND
    assert stereotypes["window_frames"] is ParamStereotype.SCALAR_RANGE
    assert stereotypes["centered"] is ParamStereotype.ENUM
    assert stereotypes["fps"] is ParamStereotype.SCALAR_RANGE
    assert ParamStereotype.SPAN not in set(stereotypes.values())


def test_the_emitted_frame_is_the_target_and_not_the_end_of_the_window() -> None:
    """The frame `k` back from the end, and the executor keys the cache on it.

    The value emitted is the series row at that frame and not the one at the end
    of the window, which is a different number rather than the same number late:
    a tool answering for the end would report the gate `k` frames into the
    future under a key that says otherwise.
    """
    params = golden_params()
    window = span_for(params, target=120)

    produced = detect_run(params, window, None)

    assert int(produced.index) == 120
    assert produced.index == window.target.index
    assert window.target.index != window[len(window) - 1].index
    assert produced.data.shape == (1, 1)
    assert produced.data.dtype == np.float32


def test_an_unplaced_count_threshold_emits_nan_rather_than_a_detection() -> None:
    """Unset means disarmed, not unbounded.

    v1 read a threshold nobody had placed as "everything passes" and painted a
    fresh session as one giant detection. Nothing is claimed here instead, and
    NaN is what a per-frame channel says that in.
    """
    params = golden_params().model_copy(update={"count_frac": None})

    produced = detect_run(params, span_for(params, target=120), None)

    assert math.isnan(float(produced.data[0, 0]))
    assert gate_series(golden_series(), params) is None


def test_the_chain_reproduces_the_v2_package_output() -> None:
    """Every array v2's `detect/` returned, bit for bit.

    Equality rather than a tolerance, as everywhere else in the Phase-4 gate,
    and across both a numpy and a scipy minor: v2's environment resolves 2.4.6
    and 1.17.1 against this one's 2.5.1 and 1.18.0.
    """
    produced = whole_record(golden_params())

    for name in GOLDEN_NAMES:
        golden = np.load(GOLDENS / f"{GOLDEN_PREFIX}{name}.npy")
        assert produced[name].dtype == golden.dtype, name
        assert np.array_equal(produced[name], golden), name


def test_the_composition_is_the_tool_rather_than_a_second_derivation() -> None:
    """`gate_series` is what `run` calls, and it is what the golden pins.

    v2 had the chain in `core/ops/`, the composition of it in `detect/`, and a
    third assembly of the same three calls inside the runnable kernel. The
    parity above is worth nothing if the tool reaches for a different one.
    """
    params = golden_params()

    assert np.array_equal(
        gate_series(golden_series(), params),
        np.load(GOLDENS / f"{GOLDEN_PREFIX}gate.npy"),
    )


def test_the_trailing_shape_is_a_different_answer() -> None:
    """The one case that fails if this tool quietly runs the shape v2 shipped.

    A trailing window over the same series puts the event's edges half a window
    late, so the gate is a different array — which is the whole reason the parity
    target is the package output. Both halves are asserted: a trailing run that
    silently produced the centred answer would be just as wrong, and the interval
    count says the two are the same event rather than two unrelated arrays.
    """
    centred = gate_series(golden_series(), golden_params())
    trailing = gate_series(golden_series(), golden_params().model_copy(update={"centered": False}))
    assert centred is not None and trailing is not None

    assert not np.array_equal(centred, trailing)
    assert int(centred.sum()) == int(trailing.sum())
    assert int(np.argmax(trailing)) - int(np.argmax(centred)) == 7


def test_the_executor_reproduces_the_whole_record_gate_frame_by_frame() -> None:
    """The claim the centred contract buys, through the one execution path.

    Each frame is answered from a 59-frame window while the golden is a 256-frame
    transform, so this is not the same arithmetic — it is the assertion that the
    declared reach is enough for the difference to stay under the value band and
    the count threshold. A tool that declared too little lookahead would emit a
    gate that disagrees near the event's edges, which is exactly where a
    detection is claimed or not.
    """
    params = golden_params()
    node = Node(node_id="d", tool_id="detect", version="1.0.0", params=params.model_dump())
    plan = ExecutionPlan.build(
        Dag.build(Pipeline(nodes=(node,)), REGISTRY),
        source="footage|1|2",
        span=SourceSpan(start=60, end=200),
    )

    results = list(execute(plan, BlockSource()))

    golden = np.load(GOLDENS / f"{GOLDEN_PREFIX}gate.npy")
    assert [int(result.index) for result in results] == list(range(60, 200))
    produced = np.array([float(result["d"].data[0, 0]) for result in results], np.float32)
    assert np.array_equal(produced, golden[60:200].astype(np.float32))
    # And the run actually crossed the event rather than agreeing about a
    # stretch of zeros.
    assert 0.0 < float(produced.mean()) < 1.0


def test_a_series_that_is_not_frames_by_elements_is_refused() -> None:
    """The chain is denominated in elements per frame, and says so."""
    with pytest.raises(ValueError, match="2D"):
        gate_series(np.zeros((4, 4, 4), np.float32), golden_params())
    with pytest.raises(ValueError, match="at least one frame"):
        gate_series(np.zeros((0, 4), np.float32), golden_params())


def test_the_regeneration_command_names_every_golden_and_the_package() -> None:
    """A golden the recorded command does not write is a golden nobody can redo.

    The entry point is asserted by name because that is the settled parity
    target: `sieve.detect` is v2's package, and a command that had reached for
    its runnable trailing kernel instead would produce four arrays that load and
    compare exactly as well.
    """
    assert "from sieve.detect import detect" in REGENERATE
    assert "filters" not in REGENERATE
    assert GOLDEN_PREFIX in REGENERATE

    written = sorted(path.name for path in GOLDENS.glob(f"{GOLDEN_PREFIX}*.npy"))
    assert written == sorted(f"{GOLDEN_PREFIX}{name}.npy" for name in GOLDEN_NAMES)
    for value in ("(4.0, 8.0)", "(60.0, np.inf)", "(0.25, np.inf)", "window_frames=15"):
        assert value in REGENERATE


def test_detect_fills_its_three_declared_surfaces() -> None:
    """Every band's picture, at the frame the window is centred on.

    The three pairs of handles are the reason this channel exists: `freq_band`
    is in Hz, `value_band` in the incoming signal's own units and `count_frac`
    is dimensionless, so no one plot holds two of them and no axis enum could
    have named all three (`todo/a-band-has-no-stereotype-of-its-own.md`).

    What each surface is checked against is the chain itself, not a recomputed
    lookalike: the trace is the array `inband_count` compares, and the count is
    the windowed mean in the same fraction `count_frac` stores. A picture the
    detection was not computed from would be handles cutting one series while
    the gate answered for another.
    """
    params = golden_params()
    window = span_for(params, target=120)
    row = window.target_row
    series = np.stack([np.asarray(frame.data, np.float32).reshape(-1) for frame in window])
    freqs = default_freqs(params.fps)
    i, j = band_indices(freqs, params.freq_band[0], params.freq_band[1])
    power = morlet_band_power(series, params.fps, freqs, i, j, workers=1)
    windowed = windowed_mean(
        inband_count(power, params.value_band[0], params.value_band[1]),
        params.window_frames,
        params.centered,
    )

    drawn = detect_display(params, window)

    assert set(drawn) == SPEC.display_surfaces
    assert set(drawn) == {DisplaySurface.SCALOGRAM, DisplaySurface.TRACE, DisplaySurface.COUNT}
    assert all(int(frame.index) == 120 for frame in drawn.values())
    # The whole bank, not the band: the handles have to be draggable to a
    # frequency the tool is not currently summing over.
    assert drawn[DisplaySurface.SCALOGRAM].data.shape == (len(freqs), 1)
    assert j - i < len(freqs)
    assert np.array_equal(drawn[DisplaySurface.TRACE].data.reshape(-1), power[row])
    assert drawn[DisplaySurface.COUNT].data.shape == (1, 1)
    assert drawn[DisplaySurface.COUNT].data[0, 0] == pytest.approx(windowed[row] / BLOCKS)


def test_the_declared_surface_scalogram_is_the_cube_averaged_over_blocks() -> None:
    """`morlet_power_profile` is `morlet_power`'s cube, reduced inside the loop.

    The two share a pad length and a daughter and differ only in where the mean
    over blocks is taken, so this is the case that keeps the second loop from
    drifting from the first — a scalogram cut with a different pad is a picture
    of a transform the gate was not computed from. The cube exists here and
    nowhere in the tool: at a real block grid it is the memory this reduction
    is written to avoid.
    """
    series = golden_series()[:64]
    freqs = default_freqs(FPS)

    profile = morlet_power_profile(series, FPS, freqs, workers=1)
    cube = morlet_power(series, FPS, freqs, workers=1)

    assert profile.shape == (len(freqs), 64)
    assert profile.dtype == np.float32
    # Not bit-equality: the reduction is the same operation over the same
    # values, but numpy is free to pair them differently when the axis it sums
    # over is not the one it was handed.
    np.testing.assert_allclose(profile, cube.mean(axis=2), rtol=1e-6, atol=1e-6)
