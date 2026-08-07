"""`stirred_clip` earns its name: the footage that can disagree with itself.

`synthetic_video` tells its frames apart by their order and by nothing else —
each is a spatially uniform field, so every block of a frame carries the same
number (`docs/findings/2026.08.06-the-synthetic-fixture-identifies-frames-by-order.md`).
That is exact for "did every frame arrive" and empty for "did these two
implementations compute the same thing": with no spread across blocks, a value
band selects all of them or none, the count saturates, the windowed mean of a
constant is that constant, and a detector's band, threshold and window are all
unobservable in its output at once. A parity oracle run on it passes against a
front end that dropped every per-replicate pin it was handed.

So this file asserts the property the second fixture exists for rather than
assuming it, and it asserts it through the tools that will consume it —
`block_signal` for the series and `detect`'s chain for the window — because the
claim is about what those tools can see, not about pixels. Three things, and
the third is the one the fixture is named after:

* the two bursts are separated in *time* from the still footage around them,
* and in *space* from each other, one arena stirred while the other is not,
* and a detection window is **observable in the output**: at one placement of
  the bands, three window lengths give three different answers.

The last case is the fixture's whole purpose, and `TestTheRampCannotDisagree`
is what keeps it from being a claim about detectors in general — the same
measurement over `synthetic_video`, where the count is all-or-nothing at every
floor there is.

No CLI and no project here. The oracle that runs both front ends over this clip
is 05.6's, and it needs the fixture to be worth running first.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from sieve.core.types import FrameSpan
from sieve.decode.reader import VideoReader
from sieve.tools.block_signal import BlockSignalParams, BlockSignalState, Signal, grid_shape
from sieve.tools.block_signal import run as block_signal
from sieve.tools.detect import (
    band_indices,
    default_freqs,
    detect_gate,
    gate_intervals,
    inband_count,
    morlet_band_power,
    windowed_mean,
)
from tests.conftest import (
    FIXTURE_FPS,
    FIXTURE_FRAMES,
    FIXTURE_HEIGHT,
    FIXTURE_WIDTH,
    STIRRED_ARENAS,
    STIRRED_BURSTS,
)

#: The block grid every number below is denominated in. Small enough that each
#: burst covers several blocks and coarse enough that a still block is still.
BLOCK = 16

#: Frames whose *difference from their predecessor* holds a burst. A block that
#: is present on frames `first..last` is present-versus-absent on `last + 1` too,
#: so the moving pair count is one wider at the far end than the burst is.
MOVED = frozenset(
    index for first, last in STIRRED_BURSTS for index in range(first, last + 2)
)

#: How far above the still footage a burst frame has to sit. The measured ratio
#: is ~2.5e3 against the largest codec twitch in the quiet stretches; this is
#: the margin the claim is worth, not the margin it has.
BURST_MARGIN = 100.0

#: Band power below this is not counted. Measured, not chosen: it sits between
#: the 80th and 85th percentiles of this clip's own band power under the luma
#: decode, where each frame's count runs from 4 blocks to 24 of the grid's 80 —
#: the range in which a window is a question. A wide-open band counts every
#: block in every frame, and a saturated count makes the threshold, the window
#: and the gate unobservable at once, which is `TestTheRampCannotDisagree`'s
#: subject.
VALUE_FLOOR = 1e8

#: The count threshold, as a fraction of the grid's blocks. On the shoulder of
#: the windowed mean rather than at its foot, so the gate turns off and on
#: inside the record instead of covering all of it.
COUNT_FRAC = 0.25

#: Three window lengths that must not agree with each other over this clip.
WINDOWS = (5, 9, 15)


def _series(video: Path) -> NDArray[np.float32]:
    """The whole clip as `block_signal`'s `(frames, blocks)` change energy.

    Through `VideoReader` and the tool's own `run`, not through a second
    spelling of either: what the fixture is worth is what the product sees in
    it, and a hand-rolled frame difference here would let the fixture and the
    graph disagree about the very thing being measured.
    """
    params = BlockSignalParams(
        signal=Signal.CHANGE_ENERGY, block=BLOCK, scale=1.0, fps=FIXTURE_FPS
    )
    state = BlockSignalState()
    rows = []
    with VideoReader(video, luma=True) as reader:
        for index in range(reader.metadata.frame_count):
            emitted = block_signal(params, FrameSpan((reader.read(index),)), state)
            rows.append(np.asarray(emitted.data, np.float32))
    return np.stack(rows)


def _arena_blocks(arena: tuple[int, int, int, int]) -> NDArray[np.bool_]:
    """Mask of the blocks whose centre falls inside `arena`.

    Centres rather than overlap, because a block straddling the boundary
    belongs to whichever arena holds most of it, and the two arenas share a
    band of rows.
    """
    ny, nx = grid_shape(FIXTURE_HEIGHT, FIXTURE_WIDTH, BLOCK)
    x, y, width, height = arena
    rows = (np.arange(ny) + 0.5) * BLOCK
    cols = (np.arange(nx) + 0.5) * BLOCK
    inside_y = (rows >= y) & (rows < y + height)
    inside_x = (cols >= x) & (cols < x + width)
    return np.outer(inside_y, inside_x)


@pytest.fixture(scope="module")
def series(stirred_clip: Path) -> NDArray[np.float32]:
    return _series(stirred_clip)


class TestTheClipHoldsTwoEventsAndNothingElse:
    def test_the_series_covers_the_clip_on_the_grid_it_claims(
        self, series: NDArray[np.float32]
    ) -> None:
        assert series.shape == (FIXTURE_FRAMES, *grid_shape(FIXTURE_HEIGHT, FIXTURE_WIDTH, BLOCK))

    def test_every_burst_frame_outruns_every_still_frame(
        self, series: NDArray[np.float32]
    ) -> None:
        """Separation in time, as a margin rather than as a threshold.

        Frame 0 is excluded from both sides: `block_signal` has no predecessor
        for it and emits zeros by contract, which is neither a burst nor a
        measurement of the still footage.
        """
        total = series.reshape(FIXTURE_FRAMES, -1).sum(axis=1)
        moved = np.array([total[i] for i in range(1, FIXTURE_FRAMES) if i in MOVED])
        still = np.array([total[i] for i in range(1, FIXTURE_FRAMES) if i not in MOVED])

        assert moved.size and still.size
        assert moved.min() > still.max() * BURST_MARGIN

    def test_each_burst_stirs_one_arena_while_the_other_is_still(
        self, series: NDArray[np.float32]
    ) -> None:
        """Separation in space, which is what makes two replicates two answers.

        Without it a parity test comparing two arenas would be comparing one
        signal against itself under two names, and every per-replicate pin
        could be dropped with the assertions still green.
        """
        masks = [_arena_blocks(arena) for arena in STIRRED_ARENAS]

        for stirred, (first, last) in enumerate(STIRRED_BURSTS):
            during = series[first : last + 2]
            energy = [float(during[:, mask].sum()) for mask in masks]
            quiet = 1 - stirred
            assert energy[stirred] > energy[quiet] * BURST_MARGIN, (
                f"burst {stirred} did not stay in its arena: {energy}"
            )


class TestAWindowIsObservableInTheOutput:
    """The property the fixture is named for, through `detect`'s own chain."""

    def test_the_in_band_count_is_neither_empty_nor_saturated(
        self, series: NDArray[np.float32]
    ) -> None:
        """A band that some blocks are in and others are not, every frame.

        This is the precondition for everything below: a count pinned at 0 or
        at the block total carries no shape for a window to average and no
        shoulder for a threshold to sit on.
        """
        count = _count(series)
        blocks = series.shape[1] * series.shape[2]

        assert 0 < count.min()
        assert count.max() < blocks
        assert len(set(count.tolist())) > 2

    def test_three_window_lengths_give_three_different_answers(
        self, series: NDArray[np.float32]
    ) -> None:
        """The claim in full: same clip, same bands, the window alone moving.

        Under `synthetic_video` these are all one answer, which is why v2's
        parity oracle had to write its own footage and why this fixture exists.
        """
        count = _count(series)
        blocks = series.shape[1] * series.shape[2]
        answers = [
            gate_intervals(
                detect_gate(windowed_mean(count, window, True), COUNT_FRAC * blocks, np.inf)
            )
            for window in WINDOWS
        ]

        assert len({tuple(answer) for answer in answers}) == len(WINDOWS), answers

    def test_every_window_claims_one_bounded_event_inside_the_record(
        self, series: NDArray[np.float32]
    ) -> None:
        """Different is not enough — the answers have to be events.

        Three ways of claiming nothing are three different answers too, and a
        gate covering the whole record is a fourth. What a consumer needs from
        this clip is a detection with two ends inside the footage, from every
        window, so the disagreement above is one about *where* an event was and
        not about whether the detector fired at all.
        """
        count = _count(series)
        blocks = series.shape[1] * series.shape[2]

        for window in WINDOWS:
            gate = detect_gate(windowed_mean(count, window, True), COUNT_FRAC * blocks, np.inf)
            intervals = gate_intervals(gate)
            assert len(intervals) == 1, (window, intervals)
            start, end = intervals[0]
            assert 0 < start < end < FIXTURE_FRAMES


class TestTheRampCannotDisagree:
    """The contrast that keeps the file from being a claim about detectors.

    Everything above would read as "a windowed detector responds to its window"
    without this: the same measurement over `synthetic_video` shows the fixture
    it replaces cannot support the question at all.
    """

    def test_every_block_of_a_frame_carries_the_same_signal(
        self, synthetic_video: Path
    ) -> None:
        """The root cause, measured on the series rather than argued from the
        writer: a uniform field has no spatial gradient, so every block of a
        frame reduces to the same number and no value band can select a subset
        of them."""
        spread = np.ptp(_series(synthetic_video).reshape(FIXTURE_FRAMES, -1), axis=1)

        assert spread.max() < 1e-6

    def test_the_count_is_all_or_nothing_at_every_floor(
        self, synthetic_video: Path
    ) -> None:
        """The consequence a detector meets. Floors are taken from the ramp's
        own band power, so this is not the stirred clip's scale applied to
        footage that never reaches it."""
        power = _band_power(_series(synthetic_video))
        blocks = power.shape[1]

        for percentile in (25, 50, 75, 90):
            count = inband_count(power, float(np.percentile(power, percentile)), np.inf)
            assert set(count.tolist()) <= {0.0, float(blocks)}, percentile


def _band_power(series: NDArray[np.float32]) -> NDArray[np.float32]:
    """The whole bank's power per block per frame — `detect`'s first step."""
    flat = series.reshape(series.shape[0], -1)
    freqs = default_freqs(FIXTURE_FPS)
    lo, hi = band_indices(freqs, 0.0, np.inf)
    return morlet_band_power(flat, FIXTURE_FPS, freqs, lo, hi, workers=1)


def _count(series: NDArray[np.float32]) -> NDArray[np.float32]:
    """Blocks per frame whose band power sits above `VALUE_FLOOR`."""
    return inband_count(_band_power(series), VALUE_FLOOR, np.inf)
