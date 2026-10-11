"""Decode one video with OpenCV, holding recently decoded frames in memory."""

from __future__ import annotations

import threading
from collections import OrderedDict
from pathlib import Path

import cv2
import numpy as np


class VideoSource:
    """Gray frames by row. Sequential reads step the decoder; anything else seeks.

    The hold dict is the first optimization hook: every tool that asks for a
    row already decoded during this window gets it back without touching the
    decoder. It is bounded by count, not by what anybody declared.
    """

    def __init__(self, path: str | Path, hold: int = 2000) -> None:
        self.path = Path(path)
        self._cap = cv2.VideoCapture(str(self.path))
        if not self._cap.isOpened():
            raise OSError(f"could not open {self.path}")
        self.count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = float(self._cap.get(cv2.CAP_PROP_FPS)) or 30.0
        self.width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._next = 0
        self._hold: OrderedDict[int, np.ndarray] = OrderedDict()
        self._limit = hold
        self._lock = threading.Lock()
        self.decodes = 0
        self.key = f"{self.path.name}:{self.path.stat().st_size}"

    def frame(self, row: int) -> np.ndarray:
        row = int(np.clip(row, 0, self.count - 1))
        with self._lock:
            held = self._hold.get(row)
            if held is not None:
                self._hold.move_to_end(row)
                return held
            if row != self._next:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, row)
            ok, bgr = self._cap.read()
            self.decodes += 1
            if not ok:
                raise OSError(f"decode failed at row {row} of {self.path.name}")
            self._next = row + 1
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            self._hold[row] = gray
            while len(self._hold) > self._limit:
                self._hold.popitem(last=False)
            return gray

    def close(self) -> None:
        self._cap.release()
