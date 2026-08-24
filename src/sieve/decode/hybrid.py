"""Two decoders on one file, each serving what it measured fastest at.

Software threads win sequential throughput; hardware wins seek latency — but
only sometimes, and which way it falls depends on the GPU, the core count and
the frame size rather than on anything knowable from here. On one measured box
hardware won only above roughly four megapixels
(`experiments/decode-experiments/results/02-random-access-*.json`). So the pair
is raced once at open, the verdict is cached per machine and source shape, and
the loser of the race carries nothing.

**The warmup seek is discarded, and this is the trap.** The first hardware seek
pays CUDA initialisation and is several times the sustained figure, so a race of
one seek per side routes the pair backwards and then caches the mistake. Same
discipline as every experiment in this tree: a warm-up is thrown away and the
best of the counted attempts wins.

**Where this earns its keep is narrow, and saying so is the point.** Against a
derived file — a display proxy, a cut — every route is interactive and the
differences shrink to single digits, which is
`docs/findings/2026.08.21-decode-stack-best-combinations.md`'s finding that file
choice dominates route choice. This class is for the uncut original, in the
window before derived files exist and wherever a committed action needs exact
source pixels. Building it over a proxy is not wrong, just pointless.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from sieve.decode import probe
from sieve.decode.pyav import PyAVRoute, hardware, software
from sieve.decode.route import STEP_WITHIN
from sieve.frame.shape import Shape
from sieve.frame.table import FrameTable

#: Seeks counted per side, after a discarded warm-up. Three is enough to see
#: past a single unlucky one and cheap enough to pay at open; the numbers go
#: into the cache beside the verdict so a suspicious one can be read rather
#: than merely re-run.
RACE_SEEKS = 3


class HybridRoute:
    """A software route and a hardware route, used where each measured best."""

    def __init__(self, path: Path, table: FrameTable, shape: Shape, *,
                 pix: str = "gray", step_within: int = STEP_WITHIN,
                 use_cache: bool = True):
        self.table = table
        self.step_within = step_within
        self.sw = software(path, table, pix=pix, step_within=step_within)
        self.hw = hardware(path, table, pix=pix, step_within=step_within)
        self.form = self.sw.form
        self.key = shape.probe_key()
        self.measured_ms: dict[str, float] = {}
        self.verdict = "sw"
        self.from_cache = False

        if self.hw is None:
            self.verdict = "sw"
        else:
            cached = probe.get(self.key) if use_cache else None
            if cached:
                self.verdict = cached.get("verdict", "sw")
                self.measured_ms = cached.get("measured_ms", {})
                self.from_cache = True
            else:
                self._race()
                probe.store(self.key, self.verdict, self.measured_ms)
            if self.verdict == "sw":
                # the loser carries nothing: an open hardware decoder holds a
                # device context and a share of the file's page cache for a
                # route that has been measured not to be used
                self.hw.close()
                self.hw = None

    @property
    def pos(self) -> int:
        return self.hw.pos if self.verdict == "hw" and self.hw else self.sw.pos

    def _race(self) -> None:
        """Seek each side to the same distant rows and keep the best of each."""
        rows = len(self.table)
        for side, route, base in (("sw", self.sw, rows // 3),
                                  ("hw", self.hw, 2 * rows // 3)):
            times: list[float] = []
            for attempt in range(RACE_SEEKS + 1):
                row = min(rows - 1, base + 7 * attempt)
                start = time.perf_counter()
                route.at(row)
                times.append((time.perf_counter() - start) * 1000)
            self.measured_ms[side] = min(times[1:])  # the first pays warmup
        self.verdict = ("hw" if self.measured_ms["hw"] <= self.measured_ms["sw"]
                        else "sw")

    # ── answering ────────────────────────────────────────────────────────
    def at(self, row: int) -> tuple[np.ndarray, str] | None:
        parked = self._parked_side(row)
        if parked is not None:
            side, route = parked
        elif self.verdict == "hw" and self.hw is not None:
            side, route = "hw", self.hw
        else:
            side, route = "sw", self.sw
        answer = route.at(row)
        return None if answer is None else (answer[0], f"{side} {answer[1]}")

    def _parked_side(self, row: int) -> tuple[str, PyAVRoute] | None:
        """Whichever decoder can step to `row`, software preferred.

        Stepping beats seeking on either side, so a decoder already in position
        answers regardless of which one won the race — the verdict decides who
        pays for a *jump*, which is the only thing it measured.
        """
        for side, route in (("sw", self.sw), ("hw", self.hw)):
            if route is None:
                continue
            if 0 < row - route.pos <= self.step_within:
                return side, route
        return None

    def keyframe_at(self, row: int) -> tuple[np.ndarray, int, str] | None:
        route = self.hw if (self.verdict == "hw" and self.hw) else self.sw
        side = "hw" if route is self.hw else "sw"
        answer = route.keyframe_at(row)
        if answer is None:
            return None
        image, landed, label = answer
        return image, landed, f"{side} {label}"

    def close(self) -> None:
        self.sw.close()
        if self.hw is not None:
            self.hw.close()
