"""The display tier: the whole recording at display sampling, built behind you.

What a scrub *outside* the filled window is served from. Inside a window every
route is a few milliseconds; one position past it there was nothing at all and
the picture held still, because the only tier left was the source and the
drawing thread may not pay a seek
(`docs/findings/2026.08.22-what-froze-the-felt-loop.md`: 200-370 ms per drag
into unfilled ground is what "frozen" was, and the kf-snap route that avoids
building anything is 150-180 ms, which is the same complaint).

**It is the chunk store and the window fill, at a coarser form over the whole
extent.** That is not a shortcut; it is what a proxy *is* — complete spans of
one form on disk, random-accessible by ordinal. The session explorer built its
proxy as 96-frame intra segments and this tree already has that machinery,
written from the same measurements: lossy intra because
`docs/findings/2026.08.21-lossy-intra-beats-lossless-for-the-cut.md` prices it
against four alternatives, and 96 positions because that is the grid a window
snaps to. A second implementation would be a second set of rules about partial
spans and generations, disagreeing with the first one eventually.

**The build follows attention and is redirectable, which is measured rather
than assumed.** `experiments/storage-experiments/results/06-build-order-*`
prices exactly this freedom: the region in 4-segment batches costs about 5%
over one linear pass, scattered order costs nothing beyond that, and a
mid-build redirect to a far segment is ~1.3 s to the first usable segment
there. `WindowFill._order` already starts at the anchor's chunk and wraps, so
redirecting is stopping one and launching the next.

**Its pixels are for looking at and are never admitted.** A proxy frame is at
a resampled form, so `forms.grade` grades anything derived from it `APPROX` —
`experiments/tool-experiments/forms.py`'s law, *derived is for looking at,
decoded is for recording*. Nothing here writes to the store's cache; the
serving tier that calls `fetch` does not either, and that is where the rule
has teeth.

**What it costs is a full read of the recording, once, in the background.**
The explorer paid it out of process with the scale pushed down into
libavfilter — free, per
`docs/findings/2026.08.21-sequential-luma-ceiling-is-shared.md`, where piping
full-resolution frames back is not. Here the frames come back through the
source contract at source form and are shaped in `forms.build`, which pays the
full-resolution decode either way and adds a downscale of about a millisecond.
Out-of-process would need SIEVE to name a container and demux, which is the
line ADR-0009 draws and the reason `chunks.py` encodes what the substrate
already held rather than transcoding a file.

Nothing here imports Qt.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np

from sieve.chunks import CHUNK_FRAMES, ChunkStore
from sieve.contract.forms import Form
from sieve.fill import Readers, WindowFill, WriteBehind
from sieve.store import Frames

#: The long edge a proxy is built at. A quarter of the 5.3K footage in
#: `video-tests/` is 1328, which is what the session explorer used and what
#: every drag timed on it was timed through; this is that rounded to a display
#: width, and it is a ceiling — a recording already smaller is not upscaled,
#: because a proxy larger than its source costs more and shows less.
PROXY_LONG_EDGE = 1280

#: Frames the build keeps in RAM. It is not filling a cache — the window's
#: budget is for the window's form — so this is just the handful a chunk is
#: assembled through before it is queued.
_BUILD_BUDGET = 8

#: Chunks of the proxy held open at once, against the three a window fill
#: wants. A scrub outside the filled window is what this tier is for, and it
#: has no locality by definition: consecutive drag steps land in different
#: chunks, and reopening one is the entire cost of the route. Enough to cover
#: a scrub's neighbourhood, not enough to hold a long recording open —
#: sixty-four chunks is a little over an hour and a half of 24 fps footage
#: at ninety-six positions each, and the containers are small.
_OPEN_CHUNKS = 64


def proxy_form(source: Form, long_edge: int = PROXY_LONG_EDGE) -> Form:
    """The whole frame, gray, scaled so its long edge is at most *long_edge*.

    Gray because the tuning loop is gray and a chunk is written from gray;
    whole-frame because the proxy is what a scrub over the *file* is served
    from, and a crop drawn on it needs the picture the crop is cut out of.

    Even on both axes: a chunk encodes through yuv420p, which halves both
    chroma dimensions and cannot describe an odd one.
    """
    width, height = source.out
    scale = min(1.0, long_edge / max(width, height))
    out = tuple(max(2, round(value * scale) - round(value * scale) % 2)
                for value in (width, height))
    return Form(source.rect, out, "gray")


class Proxy:
    """One recording at display sampling, filling in behind the user.

    Owns its own chunk store, writer and cache, all separate from the
    window's: the two tiers hold different forms, and one budget shared
    between a 300-frame window and a whole-file build is the window being
    evicted by its own placeholder.
    """

    def __init__(
        self,
        positions: tuple[int, ...],
        source: Form,
        readers: Readers,
        holes: set[int] | None = None,
    ) -> None:
        self.positions = positions
        self.form = proxy_form(source)
        self.chunks = ChunkStore(
            Path(tempfile.gettempdir()) / f"sieve-proxy-{os.getpid()}",
            open_chunks=_OPEN_CHUNKS,
        )
        self.writer = WriteBehind(self.chunks)
        self.readers = readers
        self.holes = holes
        self._cache = Frames(budget=_BUILD_BUDGET)
        self._fill: WindowFill | None = None

    def build(self, anchor: int = 0) -> None:
        """Start, or move, the frontier — the whole extent, *anchor* first.

        Not waited on when it displaces a running build, for the reason a
        landing does not wait: the frames a dying frontier still writes are
        the same form into the same store, so they are chunks that were going
        to be written anyway.
        """
        if not self.positions:
            return
        if self._fill is not None:
            self._fill.stop(wait=False)
        self._fill = WindowFill(
            self.positions, 0, len(self.positions), anchor, self.form,
            self._cache, self.chunks, self.writer, self.readers,
            holes=self.holes,
        )
        self._fill.launch()

    def building(self) -> bool:
        return self._fill is not None and self._fill.running()

    def covered(self) -> int:
        """Positions that have a chunk on disk. Asked, never remembered."""
        starts = self.chunks.persisted()
        return sum(min(len(self.positions), start + CHUNK_FRAMES) - start
                   for start in starts)

    def fetch(self, ordinal: int) -> np.ndarray | None:
        """The proxy frame at *ordinal*, or None where the build has not been.

        A miss is the ordinary answer early in a session and is not a hole:
        the build is still on its way here, so a caller asks again next time
        rather than recording anything.
        """
        return self.chunks.fetch(ordinal)

    def close(self) -> None:
        """Stop the frontier, drop what is queued, and take the files.

        The queue is thrown away rather than drained: what is in it is for a
        recording that is closing, and the directory it would be written into
        is about to go.
        """
        if self._fill is not None:
            self._fill.stop()
            self._fill = None
        self.writer.drain()
        self.chunks.destroy()
