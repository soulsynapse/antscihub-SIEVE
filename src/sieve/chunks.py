"""Write-behind persistence: a window that was filled once refills at cut speed.

Invariants: a window snaps to the chunk grid so overlapping windows share
chunks. Existence is read from the directory, never inferred. Only complete
chunks are written — a partial one is indistinguishable from whole on disk.
The scratch directory is per-process and dies with the session.
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

#: Positions per chunk — four GOPs of the test footage.
CHUNK_FRAMES = 96

#: Open containers held for reading; sized for fill-vs-draw contention.
DEFAULT_OPEN_CHUNKS = 3

_CODEC, _CRF, _PRESET, _RATE = "libx264", "18", "veryfast", 24


def _pts_helpers(stream) -> tuple[Any, Fraction]:
    """Local index to pts, and the tick distance between two frames.

    Chunk timebase is ours and exact; source pts arithmetic does not apply.
    """
    base = stream.start_time or 0
    step = Fraction(1, 1) / (stream.average_rate * stream.time_base)
    return (lambda i: base + int(step * i)), step


def _luma_plane(frame) -> np.ndarray:
    """Plane 0 out of a decoded chunk frame, the decoder's padding dropped."""
    plane = frame.planes[0]
    flat = np.frombuffer(plane, dtype=np.uint8)[: frame.height * plane.line_size]
    return flat.reshape(frame.height, plane.line_size)[:, : frame.width]


class ChunkStore:
    """Complete chunks of one form on disk, written behind a fill.

    One form at a time — a form change wipes. The generation counter in the
    filename makes a file an encoder still holds invisible without deleting it.
    """

    def __init__(self, directory: Path | None = None,
                 open_chunks: int = DEFAULT_OPEN_CHUNKS) -> None:
        self.directory = directory or Path(tempfile.gettempdir()) / (
            f"sieve-chunks-{os.getpid()}"
        )
        self.open_chunks = max(1, open_chunks)
        self.directory.mkdir(parents=True, exist_ok=True)
        #: bumped by `wipe`; filenames carry it so stale survivors are invisible
        self._generation = 0
        #: open readers, MRU last; the lock covers only this dict
        self._open: OrderedDict[int, Any] = OrderedDict()
        self._readers: dict[int, threading.Lock] = {}
        self._lock = threading.Lock()

    # -- what is on disk ---------------------------------------------------

    def _path(self, start: int, generation: int | None = None) -> Path:
        gen = self._generation if generation is None else generation
        return self.directory / f"chunk-{gen:04d}-{start:08d}.mp4"

    def persisted(self) -> set[int]:
        """Chunk starts of this generation, globbed fresh each call."""
        return {
            int(path.stem.split("-")[2])
            for path in self.directory.glob(f"chunk-{self._generation:04d}-*.mp4")
        }

    # -- writing -----------------------------------------------------------

    @property
    def generation(self) -> int:
        """Current form-lifetime; a fill captures it at queue time so a stale
        encode writes into its own generation and is never read back."""
        return self._generation

    def encode(
        self,
        start: int,
        frames: list[np.ndarray],
        form: Form,
        generation: int,
    ) -> None:
        """Write one complete chunk. Runs on the write-behind thread only.

        The per-frame sleep yields the GIL so the drawing thread is not
        starved while a chunk encodes.
        """
        if form.pix != "gray":
            raise ValueError(
                f"a chunk is written from gray; {form.key()} is {form.pix}"
            )
        width, height = form.out
        # Write to .part then os.replace so a chunk is visible only once whole.
        # format="mp4" is explicit: av.open infers from extension, and .part
        # would produce no muxer.
        final = self._path(start, generation)
        partial = final.with_name(final.name + ".part")
        with av.open(str(partial), "w", format="mp4") as out:
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
        os.replace(partial, final)

    # -- reading -----------------------------------------------------------

    def fetch(self, ordinal: int) -> np.ndarray | None:
        """The frame at *ordinal*, out of its chunk, or None if unwritten.

        The shared lock covers only the open table; each chunk has its own
        reader lock, so two chunks decode concurrently.
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
                while len(self._open) > self.open_chunks:
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
        """Drop everything for a form change. Blocks.

        Generation moves first, unlink is best-effort — a file an encoder
        still holds survives the delete but is invisible to the new generation.
        """
        with self._lock:
            self._generation += 1
            for container in self._open.values():
                container.close()
            self._open.clear()
            self._readers.clear()
        # `chunk-*` not `chunk-*.mp4` — a .part still being encoded must go too
        for path in self.directory.glob("chunk-*"):
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
