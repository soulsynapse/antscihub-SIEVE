"""The synthetic source: frames from arithmetic, shaped by whatever is being tested.

The third source, and the only one with no file behind it. `docs/decode/ideas.md`
argues it earns its place twice: a protocol derived from one backend is that
backend wearing an interface's clothes, and a synthetic backend is also how the
canvas gets tested against injected latency, drops and out-of-order arrival with
no codec involved.

It is not a recording and is never proposed as one. It is the instrument for
asking what SIEVE does with a source that is not a video file — and every answer
it gives is reproducible, because the pixels are computed rather than decoded.

**The address is not a path.** `synthetic:frames=500,access=forward` is the whole
source. `Source.handles` takes a `str` and the contract never says it names a
file, which is the clause this tool is here to hold open: a camera, a socket and
a generator all have addresses and none of them have paths.

**It can be forward-only.** `Access.FORWARD` has been declared by nothing and read
by nothing since `edges.py` was written. Here it is real: with `access=forward`
the source serves the head and refuses anything behind it, which is what a live
camera does and what a container never does.

**Its extent can grow.** With `grow=N` the source lists N more positions on every
`extent()` call, up to `frames`. A caller that asks twice gets two answers, and
one that asked once at open is holding a number that was true then.

**It can refuse deliberately.** `drop=k` makes every k-th position list and read
back `None` — the mid-GOP prefix's shape, on demand, at any position rather than
only at the head, and with no seek to pay to discover it.

Nothing here is random. `latency` sleeps a fixed time so a probe measures a
number it chose, and the frame content is a pure function of the position, so a
test may assert exact pixels rather than that something arrived.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import numpy as np

from sieve.contract import Tool
from sieve.contract.edges import (
    FRAME,
    Access,
    Edge,
    Extent,
    FrameSpec,
    Origin,
    Positioning,
    Timebase,
)
from sieve.contract.forms import source_form
from sieve.contract.nodes import Fingerprint, Opened, Output, Source

#: What an address must start with for this tool to claim it.
SCHEME = "synthetic:"

#: Settings and their defaults. A caller names the ones it cares about.
_DEFAULTS: dict[str, int | str] = {
    "frames": 300,          #: positions in the full extent
    "width": 640,
    "height": 360,
    "access": "random",     #: random | forward
    "grow": 0,              #: positions revealed per extent() call; 0 = all at once
    "drop": 0,              #: every k-th position reads back None; 0 = none
    "latency": 0,           #: milliseconds a read sleeps before answering
    "tick": 1001,           #: ticks between positions, in the timebase below
    "rate": 24000,          #: timebase numerator... ticks per second is rate/1001
}


def _settings(address: str) -> dict[str, int | str]:
    """Parse `synthetic:key=value,key=value`. Unknown keys are an error.

    An error rather than ignored: a misspelled knob that silently does nothing
    is a test that quietly measures the default and reports it as the setting.
    """
    found = dict(_DEFAULTS)
    body = address[len(SCHEME):].strip()
    for clause in (part for part in body.split(",") if part.strip()):
        key, _, value = clause.partition("=")
        key = key.strip()
        if key not in _DEFAULTS:
            raise ValueError(f"{key!r} is not a synthetic source setting")
        found[key] = value.strip() if isinstance(_DEFAULTS[key], str) else int(value)
    if found["access"] not in ("random", "forward"):
        raise ValueError(f"access is random or forward, not {found['access']!r}")
    return found


class _Generator:
    """One open synthetic source. Private to this tool; SIEVE never sees it."""

    def __init__(self, address: str) -> None:
        self.address = address
        settings = _settings(address)
        self.frames = int(settings["frames"])
        self.width = int(settings["width"])
        self.height = int(settings["height"])
        self.forward = settings["access"] == "forward"
        self.grow = int(settings["grow"])
        self.drop = int(settings["drop"])
        self.latency = int(settings["latency"]) / 1000.0
        self.tick = int(settings["tick"])
        self.rate = int(settings["rate"])
        #: how many positions `extent` has revealed so far
        self._revealed = self.frames if self.grow <= 0 else 0
        #: the head, for a forward-only source. None until the first read.
        self._cursor: int | None = None
        self._lock = threading.Lock()
        #: every read this source has served, for a test to check against
        self.served: list[int] = []

    # -- the contract's three callables ------------------------------------

    def extent(self) -> Extent:
        with self._lock:
            if self.grow > 0:
                self._revealed = min(self.frames, self._revealed + self.grow)
            revealed = self._revealed
        listed = tuple(i * self.tick for i in range(revealed))
        return Extent(listed, closed=self.grow <= 0)

    def read(self, position: int | None) -> Any | None:
        if position is None:
            raise ValueError("a frame edge is positioned; pass a tick")
        if position % self.tick:
            raise ValueError(f"{position} is not on this source's grid")
        index = position // self.tick
        if not 0 <= index < self.frames:
            raise ValueError(f"{position} is not a frame this source listed")
        if self.forward:
            with self._lock:
                if self._cursor is not None and index <= self._cursor:
                    # What a live source does, and what `Access.FORWARD` means:
                    # "the head only, once each". Raising rather than answering
                    # None, because None means listed-and-undeliverable and this
                    # position is perfectly deliverable — to somebody who had
                    # asked in time.
                    raise ValueError(
                        f"{position} is behind the head; this source is forward-only"
                    )
                self._cursor = index
        if self.latency:
            time.sleep(self.latency)
        with self._lock:
            self.served.append(position)
        if self.drop and index % self.drop == 0:
            return None
        return self.frame_at(index)

    def frame_at(self, index: int) -> Any:
        """A pure function of the index, so a test can assert exact pixels.

        A vertical ramp that does not move, plus a block that does. The static
        half catches a source serving the wrong *form*; the moving half catches
        one serving the wrong *position*, which a flat colour would not.
        """
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        ramp = (np.arange(self.width, dtype=np.uint16) * 255 // max(1, self.width - 1))
        frame[:, :, 0] = ramp.astype(np.uint8)
        band = max(1, self.height // 8)
        top = (index * band) % max(1, self.height - band)
        frame[top:top + band, :, 2] = 255
        frame[:band, :band, 1] = np.uint8(index % 256)
        return frame

    def fingerprint(self) -> Fingerprint | None:
        """The address, because that is the whole of what this source is.

        Not `None`: a synthetic source genuinely does have a durable identity,
        and it is exactly its settings. `None` is for a source that has none — a
        camera — and claiming it here would test the wrong clause.
        """
        return Fingerprint("address", self.address)

    def close(self) -> None:
        with self._lock:
            self._cursor = None


def _handles(address: str) -> bool:
    if not address.startswith(SCHEME):
        return False
    try:
        _settings(address)
    except ValueError:
        return False
    return True


def _open(address: str) -> Opened:
    state = _Generator(address)
    edge = Edge(
        name="synthetic:0",
        kind=FRAME,
        spec=FrameSpec(source_form(state.width, state.height, "bgr")),
        at=Positioning(
            timebase=Timebase(1, state.rate),
            # Minted: nothing was read out of anything. The ticks are this
            # tool's arithmetic, which is what `Origin.MINTED` is for.
            origin=Origin.MINTED,
            access=Access.FORWARD if state.forward else Access.RANDOM,
        ),
    )
    return Opened(
        address=address,
        outputs={edge.name: Output(edge=edge, read=state.read,
                                   extent=state.extent)},
        close=state.close,
        fingerprint=state.fingerprint,
    )


TOOLS = (
    Tool(
        name="synthetic source",
        #: Bumped when a change here would produce different bytes for one
        #: position — a key over decoded pixels folds it (ADR-0010). `frame_at`
        #: is the whole of what that covers.
        version=1,
        role=Source(
            handles=_handles,
            open=_open,
            offers=(FRAME,),
            #: No pattern can express a scheme, which is the same gap the image
            #: directory source hits from the other side.
            patterns=(),
        ),
    ),
)
