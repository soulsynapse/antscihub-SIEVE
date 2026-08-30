"""One open container, absolute frame indices, and how it got there.

The decode leaf every experiment in this folder shares. It is the same
arrangement `explorer.py` carries inline: one cursor, a step forward when the
target is close enough ahead, a seek otherwise, and the route reported back
so a policy can be billed for the locality it gave up. That duplication is
deliberate for now — the explorer is a driven session with committed logs
and is not being edited underneath them — and it is the kind of duplication
that drifts, so anything learned here about the seek/step rule belongs in
both or in neither.

**The whole luma plane, copied.** A view onto `plane` keeps the entire
AVFrame alive — all three planes — so a pool of views costs half again what
it holds, and the extra is chroma nothing in this tree reads. `.copy()` and
not `ascontiguousarray`: at this width the stride equals the width, so the
slice is already contiguous and `ascontiguousarray` hands back the view it
was given, silently pinning the frame it was supposed to release.

Callers that want a crop derive one through `forms`, which stays the
authority on what a form's bytes are. Nothing here knows about forms.

**Copied byte for byte from `orchestrator-experiments/fetch.py`, and it is
the one file here that is.** The decode leaf is not what V2 changes, and a
rewritten one would put a second variable under every wall this folder
measures against V1's. It carries the same warning its original does, now
about three copies rather than two: anything learned about the seek/step
rule belongs in all of them or in none, and `diff` against V1 is the check.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import av
import numpy as np

#: Beyond this many rows ahead, a seek beats stepping. Measured in
#: `decode-experiments/03`; the value lives there and this is a use of it.
STEP_WITHIN = 60


def _pts_helpers(stream):
    tb, rate = stream.time_base, stream.average_rate
    base = stream.start_time or 0
    step = Fraction(1, 1) / (rate * tb)
    return (lambda i: base + int(step * i)), step


def luma(frame) -> np.ndarray:
    """The whole luma plane, copied out of the decoder's buffer."""
    plane = frame.planes[0]
    arr = np.frombuffer(plane, dtype=np.uint8)
    arr = arr[: frame.height * plane.line_size]
    return arr.reshape(frame.height, plane.line_size)[:, : frame.width].copy()


class Fetcher:
    """One open container with one cursor. Not thread-safe by construction.

    A second reader opens its own, which is the arrangement `nodes.py` states
    and `fill.py` relies on: two opened sources on one address read at once
    cost nothing measurable, and sharing one puts whoever is drawing behind
    the frontier's decode.
    """

    def __init__(self, path: Path, step_within: int = STEP_WITHIN) -> None:
        self.container = av.open(str(path))
        self.stream = self.container.streams.video[0]
        self.stream.thread_type = "AUTO"
        self.pts_of, self.step = _pts_helpers(self.stream)
        self.step_within = step_within
        self.size = (self.stream.codec_context.width,
                     self.stream.codec_context.height)
        self.seeks = 0
        self.steps = 0
        self._pos: int | None = None
        self._decoded = None

    @property
    def at(self) -> int | None:
        """Where the cursor is, or None before the first read."""
        return self._pos

    def reaches(self, idx: int) -> bool:
        """Would serving *idx* be a step from where the cursor stands?

        The question the rule the dispatcher finding leaves unimplemented has
        to ask: do not abandon a sequential run for a row that run will
        arrive at anyway.
        """
        if self._pos is None or self._decoded is None:
            return False
        return 0 < idx - self._pos <= self.step_within

    def exact(self, idx: int) -> tuple[np.ndarray, str]:
        """The frame at *idx*, and whether it came by step or by seek."""
        if self._decoded is not None and self._pos is not None:
            ahead = idx - self._pos
            if 0 < ahead <= self.step_within:
                try:
                    for _ in range(ahead):
                        frame = next(self._decoded)
                    self._pos = idx
                    self.steps += 1
                    return luma(frame), "step"
                except StopIteration:
                    pass
        target = self.pts_of(idx)
        half = self.step / 2
        self.container.seek(target, stream=self.stream)
        self._decoded = self.container.decode(self.stream)
        for frame in self._decoded:
            if frame.pts is not None and frame.pts + half >= target:
                self._pos = idx
                self.seeks += 1
                return luma(frame), "seek"
        raise RuntimeError(f"off the end at {idx}")

    def close(self) -> None:
        self.container.close()
