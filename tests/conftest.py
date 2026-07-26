"""Shared fixtures.

Synthetic videos rather than committed media: a fixture that has to be
downloaded is a fixture that gets skipped, and a decoder test that skips is
indistinguishable from one that passes.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np
import pytest

FIXTURE_FPS = 20.0
FIXTURE_FRAMES = 40
FIXTURE_WIDTH = 160
FIXTURE_HEIGHT = 120


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
