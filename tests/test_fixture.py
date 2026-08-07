"""The synthetic video fixture is what it claims to be.

A fixture nothing reads is a fixture that can rot green — v2 shipped several,
and the audit that found them is why this file exists before any consumer does.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from tests.conftest import FIXTURE_FRAMES, FIXTURE_HEIGHT, FIXTURE_WIDTH


def _decode(path: Path) -> list[np.ndarray]:
    capture = cv2.VideoCapture(str(path))
    try:
        frames = []
        while True:
            ok, frame = capture.read()
            if not ok:
                return frames
            frames.append(frame)
    finally:
        capture.release()


def test_frames_are_individually_identifiable(synthetic_video: Path) -> None:
    frames = _decode(synthetic_video)

    assert len(frames) == FIXTURE_FRAMES
    assert [f.shape for f in frames] == [(FIXTURE_HEIGHT, FIXTURE_WIDTH, 3)] * FIXTURE_FRAMES

    # What the fixture actually promises is ordering, not the written value:
    # mp4v quantises hard enough that the round-tripped mean drifts up to four
    # of the five levels between neighbours
    # (findings/2026.08.06-the-synthetic-fixture-identifies-frames-by-order.md).
    # A seek test can still name the frame it landed on, and no test may assert
    # `n * 5` back out of the decoder.
    blue = np.array([frame[:, :, 0].mean() for frame in frames])
    assert np.all(np.diff(blue) > 0)
    assert np.abs(blue - np.arange(FIXTURE_FRAMES) * 5).max() < 5

    # Uniform fields, not gradients: a test asserting on one pixel and a test
    # asserting on the mean must agree about which frame they are looking at.
    assert max(float(np.ptp(frame[:, :, 0])) for frame in frames) < 5.0
