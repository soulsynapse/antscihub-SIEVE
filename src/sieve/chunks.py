"""Write-behind persistence: a window that was filled once refills at cut speed.

Ported from `experiments/storage-experiments/session-explorer.py`, which is
the oracle for this whole shelf — the tier stack there was driven by hand and
measured, and every rule below is one it earned rather than one argued here.

**A chunk is the unit of persistence, eviction and coverage.** Ninety-six
positions on the store's ordinal grid, which is four GOPs of the footage in
`video-tests/` (`experiments/decode-experiments/results/02-random-access-*`).
A window snaps to this grid rather than the grid bending to the window,
because two windows that overlap must share the chunks under the overlap or
the second one re-pays the first one's decode.

**Which chunks exist is read from the directory, never inferred from a gap.**
The same discipline `store.py` keeps between `missing` and an absent key: a
chunk nobody wrote and a chunk that is genuinely nothing are the same picture
once the record is thrown away. `persisted()` globs; nothing counts frames.

**Only complete chunks are written.** A partial chunk is indistinguishable
from a whole one once it is on disk, and a fill that stopped halfway would
otherwise leave a short chunk that answers for positions it never held. The
fill hands over a buffer only when it filled the whole span.

**Lossy intra, and that is measured rather than conceded.**
`docs/findings/2026.08.21-lossy-intra-beats-lossless-for-the-cut.md` prices
five routes over exactly this shape — a 300-frame 1024-square region off the
5.3K source — and x264 CRF18 intra wins both axes it is allowed to win: 10.3
ms random access against the original's 315.5, and 22 MB against FFV1's 124.
Lossless is not the safe choice here; it is the slower and larger one,
because losslessly encoding inherited sensor noise makes the decode the new
floor.

**SIEVE holds a codec for its own cut and for nothing else.** ADR-0009's two
prohibitions are about naming a tool and reaching past the contract, and this
does neither: no source is read here, no container of anybody else's is
opened, and no tool is named. What is encoded is what the substrate already
had in RAM, in a form the substrate named. A source decoder stays the tool's,
which is the boundary the ADR draws — `pyproject.toml` carries the same note
beside the dependency.

Nothing here imports Qt. The scratch directory is per-process and dies with
the session, which is the least this can claim while `nodes.py`'s granted
scratch space does not exist yet.
"""

from __future__ import annotations

import os
import tempfile
import threading
import time
from collections import OrderedDict
from fractions import Fraction
from pathlib import Path
from typing import Any

import av
import numpy as np

from sieve.contract.forms import Form

#: Positions per chunk, on the store's ordinal grid. Four GOPs of the footage
#: in `video-tests/`, which is what the session explorer tiled its windows
#: with; a window snaps to this grid so chunks tile it exactly.
CHUNK_FRAMES = 96

#: Open containers held for reading. Three, because a fill refilling one chunk
#: while the drawing thread serves out of another is the contention this tier
#: is for, and a fourth has never been asked for.
_OPEN_CHUNKS = 3

#: What the cut is. The finding above measured this exact combination against
#: four others on this exact shape.
_CODEC, _CRF, _PRESET, _RATE = "libx264", "18", "veryfast", 24


def _pts_helpers(stream) -> tuple[Any, Fraction]:
    """Local index to pts, and the tick distance between two frames.

    A chunk is written by this module at a fixed rate, so its timebase is
    ours and the arithmetic is exact — unlike a source's, where ADR-0004's
    carried pts is the identity and a frame number is not.
    """
    base = stream.start_time or 0
    step = Fraction(1, 1) / (stream.average_rate * stream.time_base)
    return (lambda i: base + int(step * i)), step


def _luma_plane(frame) -> np.ndarray:
    """Plane 0 out of a decoded chunk frame, the decoder's padding dropped.

    The same quantity that went in — a source's luma, cropped — through one
    lossy encoder and back. A chunk is a cut of what was already held, so the
    only difference between what was written and what is read is CRF 18, which
    is the trade the finding above priced.
    """
    plane = frame.planes[0]
    flat = np.frombuffer(plane, dtype=np.uint8)[: frame.height * plane.line_size]
    return flat.reshape(frame.height, plane.line_size)[:, : frame.width]


class ChunkStore:
    """Complete chunks of one form on disk, written behind a fill.

    One form at a time, because a form change wipes: a stored small frame
    cannot become a different one, and a chunk that outlived the form it was
    written in would answer a read with the wrong pixels rather than with
    nothing.

    **A wipe changes the generation rather than trusting the unlink.** The
    explorer deleted the files and tolerated an `OSError` on the one an
    encoder still held — which leaves a chunk of the *old* form on disk, where
    `persisted` lists it and the next fill refills the new form out of it.
    Nothing goes wrong until somebody reads those pixels. Naming the
    generation in the file means a survivor is simply not seen: it is
    unreachable the moment the counter moves, and swept when the session ends.
    """

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or Path(tempfile.gettempdir()) / (
            f"sieve-chunks-{os.getpid()}"
        )
        self.directory.mkdir(parents=True, exist_ok=True)
        #: bumped by `wipe`; what is written and read carries it, so a file the
        #: previous form left behind cannot be found by the current one
        self._generation = 0
        #: open readers, most recently used last. The lock covers this dict
        #: and nothing else — see `fetch`.
        self._open: OrderedDict[int, Any] = OrderedDict()
        self._readers: dict[int, threading.Lock] = {}
        self._lock = threading.Lock()

    # -- what is on disk ---------------------------------------------------

    def _path(self, start: int, generation: int | None = None) -> Path:
        gen = self._generation if generation is None else generation
        return self.directory / f"chunk-{gen:04d}-{start:08d}.mp4"

    def persisted(self) -> set[int]:
        """Chunk starts of *this* generation, asked now rather than remembered.

        The same reason `Store.positions` is a property: a chunk lands while
        somebody is reading, and a set captured at open would hide it.
        """
        return {
            int(path.stem.split("-")[2])
            for path in self.directory.glob(f"chunk-{self._generation:04d}-*.mp4")
        }

    # -- writing -----------------------------------------------------------

    @property
    def generation(self) -> int:
        """Which form-lifetime is current. A fill captures this when it queues
        a chunk, so an encode still running when the form changed writes into
        the generation it was filled for and is never read back."""
        return self._generation

    def encode(
        self,
        start: int,
        frames: list[np.ndarray],
        form: Form,
        generation: int,
    ) -> None:
        """Write one complete chunk. Runs on the write-behind thread only.

        The per-frame yield is not decoration. Encoding is a C loop holding
        the GIL, and the session explorer measured the event loop starved for
        100-400 ms at a stretch without it; a millisecond between frames costs
        about a tenth of a second per chunk and is what lets the drawing thread
        breathe while a landing is still being written behind.
        """
        if form.pix != "gray":
            raise ValueError(
                f"a chunk is written from gray; {form.key()} is {form.pix}"
            )
        width, height = form.out
        with av.open(str(self._path(start, generation)), "w") as out:
            stream = out.add_stream(_CODEC, rate=_RATE)
            stream.width, stream.height = width, height
            stream.pix_fmt = "yuv420p"
            stream.options = {"crf": _CRF, "preset": _PRESET, "g": "1"}
            for array in frames:
                picture = av.VideoFrame.from_ndarray(array, format="gray")
                for packet in stream.encode(picture.reformat(format="yuv420p")):
                    out.mux(packet)
                time.sleep(0.001)
            for packet in stream.encode():
                out.mux(packet)

    # -- reading -----------------------------------------------------------

    def fetch(self, ordinal: int) -> np.ndarray | None:
        """The frame at *ordinal*, out of its chunk, or None if unwritten.

        **The decode does not run under the shared lock**, which is the one
        thing this port does not carry from the explorer. There the lock was
        held across an open, a seek and a decode, so a fill refilling one
        chunk stalled a drawing thread reading a different one — the freeze
        `store.py` forbids in as many words. The shared lock covers the open
        table; each reader carries its own, so two chunks are read at once and
        one chunk is never read twice at once.
        """
        start = ordinal - ordinal % CHUNK_FRAMES
        with self._lock:
            container = self._open.get(start)
            if container is None:
                path = self._path(start)
                if not path.exists():
                    return None
                container = av.open(str(path))
                self._open[start] = container
                self._readers[start] = threading.Lock()
                while len(self._open) > _OPEN_CHUNKS:
                    evicted, old = self._open.popitem(last=False)
                    self._readers.pop(evicted, None)
                    old.close()
            self._open.move_to_end(start)
            reader = self._readers[start]
        with reader:
            try:
                stream = container.streams.video[0]
                pts_of, step = _pts_helpers(stream)
                target = pts_of(ordinal - start)
                container.seek(target, stream=stream)
                for frame in container.decode(stream):
                    if frame.pts is not None and frame.pts + step / 2 >= target:
                        return np.ascontiguousarray(_luma_plane(frame))
            except av.FFmpegError:
                return None   # a chunk wiped mid-read; the fill re-derives it
        return None

    # -- letting go --------------------------------------------------------

    def wipe(self) -> None:
        """Everything, because a form changed. Blocks; the caller must want that.

        A form change is the one moment a fill may not be left to die on its
        own: the frames still landing are the old form, and they must stop
        arriving before what they were written into is thrown away.

        The generation moves first and the unlink is best-effort second, which
        is the order that matters. A file an encoder still holds survives the
        delete and is invisible anyway.
        """
        with self._lock:
            self._generation += 1
            for container in self._open.values():
                container.close()
            self._open.clear()
            self._readers.clear()
        for path in self.directory.glob("chunk-*.mp4"):
            try:
                path.unlink()
            except OSError:
                pass   # an encoder still holds it; the directory dies with us

    def destroy(self) -> None:
        self.wipe()
        try:
            self.directory.rmdir()
        except OSError:
            pass
