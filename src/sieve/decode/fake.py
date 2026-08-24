"""A route with no file behind it, so everything above one can be checked.

The most useful thing in this package and the reason `Route` is only three
methods. A fill order, an eviction rule, a tier ladder and a retention policy
are all decisions about *which rows get asked for, and when* — none of them is
about pixels, and every one of them was previously untestable because observing
it meant decoding video, owning a GPU, and waiting.

Three properties make it worth trusting.

**Every frame says which row it is.** The row is written into the frame as flat
blocks and recoverable with `row_in`, so a check asserts it got frame 412 rather
than asserting it got *an* array of the right shape. A store that hands back a
neighbouring frame is the failure this catches, and it is the failure a
shape-only assertion cannot see. Blocks rather than pixels because these frames
get stored, and a store worth checking encodes lossily.

**Every request is recorded.** `asked` is the ordered list of rows this route
was asked for, which is how "fill from the playhead's chunk, then wrap" stops
being four lines inside a thread body and becomes a list to compare against.

**It can be made to behave like the real file.** Rows can be declared
undecodable, which is how the head of a mid-GOP cut is reproduced without the
cut; and a per-call delay can be set, which is how a background fill and a
foreground serve can be made to interleave deterministically in a check rather
than by luck.

It is a workload and not evidence. Nothing measured against this route says
anything about what decoding costs — that is what `experiments/` and real
footage are for. What it establishes is that a policy does what it says, which
is a different question and one no amount of real footage answers more clearly.
"""

from __future__ import annotations

import threading
import time
from fractions import Fraction

import numpy as np

from sieve.frame.form import Form, source_form
from sieve.frame.table import FrameTable

#: Small enough that thousands of frames cost nothing, large enough to carry a
#: row marker and survive a crop in a check.
WIDTH, HEIGHT = 64, 48

#: Side of one row-marker block, in pixels. Wide enough that a lossy encode
#: leaves its median alone.
MARK = 8


def table(rows: int, *, gop: int = 24, step: int = 1001,
          head: int = 0, timebase: Fraction = Fraction(1, 24_000)) -> FrameTable:
    """A frame table with no file under it.

    `head` shifts the timestamps negative by that many frames, which is the
    shape of a source cut mid-GOP: rows exist and carry honest timestamps that
    sit below the stream's stated start. Pair it with `undecodable=range(head)`
    to reproduce this tree's footage exactly.
    """
    stamps = np.array([(i - head) * step for i in range(rows)], dtype=np.int64)
    keyframes = np.zeros(rows, dtype=bool)
    keyframes[::gop] = True
    return FrameTable(pts=stamps, keyframe=keyframes, timebase=timebase,
                      start_pts=0)


class FakeRoute:
    """Synthetic frames, an honest position, and a record of what was asked."""

    def __init__(self, frame_table: FrameTable, *, pix: str = "gray",
                 undecodable: set[int] | range | None = None,
                 delay_s: float = 0.0, step_within: int = 60):
        self.table = frame_table
        self.form: Form = source_form(WIDTH, HEIGHT, pix)
        self.undecodable = set(undecodable or ())
        self.delay_s = delay_s
        self.step_within = step_within
        self.pos = -1
        self.asked: list[int] = []
        self.decodes = 0
        self.seeks = 0
        self.steps = 0
        self._lock = threading.Lock()

    # ── frames that know their own row ───────────────────────────────────
    def image(self, row: int) -> np.ndarray:
        """The frame for a row, built the same way every time.

        Deterministic so that two routes over one table agree, which is what
        lets a check compare a cached answer against a freshly decoded one and
        mean something by the comparison.

        The row is written as four blocks rather than four pixels because these
        frames get stored, and a store worth checking encodes lossily. A marker
        one pixel wide would be smeared by the first chunk it went through, and
        the check that read it back would be reporting on the codec rather than
        on the store. `MARK` square of flat tone survives quantisation
        comfortably at the qualities this tree stores at.
        """
        arr = np.full((HEIGHT, WIDTH), row % 251, dtype=np.uint8)
        for index, byte in enumerate(int(row).to_bytes(4, "big")):
            left = index * MARK
            arr[:MARK, left:left + MARK] = byte
        if self.form.pix == "bgr":
            return np.ascontiguousarray(np.dstack([arr, arr, arr]))
        return arr

    @staticmethod
    def row_in(arr: np.ndarray) -> int:
        """Which row an array is, read back out of its own pixels.

        Each block is read as its median, so a stray quantised pixel at a block
        edge cannot change the answer — and if a block is so far gone that its
        median has moved, the frame really is not the one it claims to be.
        """
        plane = arr[..., 0] if arr.ndim == 3 else arr
        blocks = [int(np.median(plane[:MARK, i * MARK:(i + 1) * MARK]))
                  for i in range(4)]
        return int.from_bytes(bytes(blocks), "big")

    # ── answering ────────────────────────────────────────────────────────
    def at(self, row: int) -> tuple[np.ndarray, str] | None:
        if not 0 <= row < len(self.table):
            raise IndexError(f"row {row} is outside a table of "
                             f"{len(self.table)}")
        with self._lock:
            self.asked.append(row)
            stepped = 0 < row - self.pos <= self.step_within
            if stepped:
                self.steps += 1
            else:
                self.seeks += 1
        if self.delay_s:
            time.sleep(self.delay_s)
        if row in self.undecodable:
            # match the real route: park where the decoder actually got to,
            # which is the first decodable row at or after the request
            landed = next((r for r in range(row, len(self.table))
                           if r not in self.undecodable), -1)
            self.pos = landed
            return None
        self.pos = row
        with self._lock:
            self.decodes += 1
        return self.image(row), ("step" if stepped else "seek")

    def keyframe_at(self, row: int) -> tuple[np.ndarray, int, str] | None:
        if not 0 <= row < len(self.table):
            raise IndexError(f"row {row} is outside a table of "
                             f"{len(self.table)}")
        landed = self.table.keyframe_at_or_before(row)
        while landed < len(self.table) and landed in self.undecodable:
            landed += 1          # the head again: the keyframe decodes to
        if landed >= len(self.table):   # nothing and the first image is after
            return None
        with self._lock:
            self.asked.append(landed)
            self.seeks += 1
            self.decodes += 1
        if self.delay_s:
            time.sleep(self.delay_s)
        self.pos = landed
        return self.image(landed), landed, f"kf d{row - landed}"

    def close(self) -> None:
        pass

    # ── what a check reads afterwards ────────────────────────────────────
    def reset(self) -> None:
        """Forget what was asked, keeping the decoder's position.

        So a check can drive a warm-up and then assert only about the part it
        cares about, without a fresh route pretending the cache is cold.
        """
        with self._lock:
            self.asked.clear()
            self.decodes = self.seeks = self.steps = 0
