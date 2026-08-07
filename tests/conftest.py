"""Shared fixtures.

Synthetic videos rather than committed media: a fixture that has to be
downloaded is a fixture that gets skipped, and a decoder test that skips is
indistinguishable from one that passes.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from fractions import Fraction
from pathlib import Path

import cv2
import numpy as np
import pytest

# `scripts/` is not a package and must not become one — it holds repo
# machinery, not product code ("tools" is the product's word for pipeline
# steps). The tests reach it by path instead.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

FIXTURE_FPS = 20.0
#: The same rate as a container states it, which is what `VideoMetadata.fps`
#: carries. Whole here, so the two spellings agree exactly.
FIXTURE_RATE = Fraction(20)
FIXTURE_FRAMES = 40
FIXTURE_WIDTH = 160
FIXTURE_HEIGHT = 120

#: The two regions `stirred_clip`'s bursts are placed in, as `(x, y, w, h)`.
#: Plain tuples rather than `ROI`: this module is read before `sieve` is
#: importable in the ordering a fresh checkout runs, and a fixture that names a
#: product type makes the fixture's own correctness depend on it.
STIRRED_ARENAS = ((0, 0, 80, 64), (80, 56, 80, 64))

#: Each burst as `(first_frame, last_frame)` inclusive, in the same order as
#: `STIRRED_ARENAS`. The frames that *differ from their predecessor* are one
#: wider at the far end — the block is still gone-versus-present across
#: `last + 1` — which is the span a difference-based tool sees.
STIRRED_BURSTS = ((12, 18), (24, 30))

#: Background intensity range, and the seed that fixes it. Textured rather than
#: flat because a structure tensor over a flat field has vanishing spatial
#: gradients: every block reads alike and the clip inherits `synthetic_video`'s
#: problem it was built to escape.
STIRRED_BACKGROUND = (40, 90)
STIRRED_SEED = 7

#: The moving block's intensity, well clear of the background's ceiling.
STIRRED_FOREGROUND = 235

#: Fixtures whose absence is a broken environment, not an excused test. Writing
#: an mp4 is a precondition of every environment SIEVE supports, so a run that
#: could not build one has not exercised the ten test files that take these two
#: — it has hidden them. The fixtures themselves still call `pytest.skip`,
#: because the port from v2 is verbatim by decision; the correction is here.
FATAL_FIXTURE_SKIPS = frozenset({"synthetic_video", "stirred_clip"})


class FixtureUnavailable(Exception):
    """A fixture the environment is required to be able to build did not build."""


@pytest.hookimpl(wrapper=True)
def pytest_fixture_setup(fixturedef: pytest.FixtureDef, request: pytest.FixtureRequest):
    try:
        return (yield)
    except pytest.skip.Exception as skipped:
        if fixturedef.argname not in FATAL_FIXTURE_SKIPS:
            raise
        raise FixtureUnavailable(f"{fixturedef.argname}: {skipped.msg}") from skipped


@pytest.fixture(scope="session")
def synthetic_video(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """A short video whose frames are individually identifiable.

    Frame `n` is a solid field of intensity `n * 5` in the blue channel, so a
    test can assert *which* frame a seek landed on rather than merely that
    something decoded.
    """
    path = tmp_path_factory.mktemp("video") / "synthetic.mp4"
    fourcc = cv2.VideoWriter.fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, FIXTURE_FPS, (FIXTURE_WIDTH, FIXTURE_HEIGHT))
    if not writer.isOpened():
        pytest.skip("No usable mp4v encoder in this OpenCV build")

    for index in range(FIXTURE_FRAMES):
        frame = np.zeros((FIXTURE_HEIGHT, FIXTURE_WIDTH, 3), dtype=np.uint8)
        frame[:, :, 0] = index * 5
        writer.write(frame)
    writer.release()

    yield path


@pytest.fixture(scope="session")
def stirred_clip(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """Footage with motion in one arena and then the other, and nowhere else.

    `synthetic_video`'s frames are told apart by their order and by nothing
    else — spatially uniform, so every block of every frame reads alike
    (`docs/findings/2026.08.06-the-synthetic-fixture-identifies-frames-by-order.md`).
    That makes it exact for "did every frame arrive" and useless for "did these
    two implementations compute the same thing": under it a count over blocks
    saturates, a windowed mean of a constant is that constant, and a detector's
    window and thresholds are all unobservable at once. This clip is the one
    that can disagree with itself, and `tests/integration/test_stirred_clip.py`
    is where that is asserted rather than assumed.

    In v2 it lived inside `tests/gui/test_gui_cli_parity.py`, which is the whole
    reason v2's parity oracle could not run without Qt installed.
    """
    path = tmp_path_factory.mktemp("stirred") / "stirred.mp4"
    fourcc = cv2.VideoWriter.fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, FIXTURE_FPS, (FIXTURE_WIDTH, FIXTURE_HEIGHT))
    if not writer.isOpened():
        pytest.skip("No usable mp4v encoder in this OpenCV build")

    low, high = STIRRED_BACKGROUND
    background = np.random.default_rng(STIRRED_SEED).integers(
        low, high, size=(FIXTURE_HEIGHT, FIXTURE_WIDTH), dtype=np.uint8
    )
    # The two sweeps are spelled out rather than derived from `STIRRED_ARENAS`,
    # because they are not the arenas: each block travels far enough to leave
    # its arena's far edge by the end of its burst, and that is v2's footage,
    # which every band and floor measured against this clip was measured on.
    for index in range(FIXTURE_FRAMES):
        frame = np.dstack([background] * 3).copy()
        if STIRRED_BURSTS[0][0] <= index <= STIRRED_BURSTS[0][1]:
            left = 8 + (index - STIRRED_BURSTS[0][0]) * 8
            frame[8:40, left : left + 32] = STIRRED_FOREGROUND
        if STIRRED_BURSTS[1][0] <= index <= STIRRED_BURSTS[1][1]:
            left = 96 + (index - STIRRED_BURSTS[1][0]) * 6
            frame[64:100, left : left + 28] = STIRRED_FOREGROUND
        writer.write(frame)
    writer.release()

    yield path
