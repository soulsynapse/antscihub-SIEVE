"""Reading frames back out of files somebody else wrote.

One implementation, because reading a chunk this tree encoded and reading a
proxy segment ffmpeg wrote are the same act: find the file holding this instant,
open it, land on the right frame, hand back the pixels. The explorers have that
loop four times over — twice here, once for the original, once for the display
proxy — and four copies of a seek loop is one that gets fixed once.

**A row is found through the record, never through the directory.** The record
says which file holds which pts range of which form
(`sieve.store.coverage`), so a file mid-write is not present in it and a file
that vanished reads as absent rather than as an error.

**Inside a file, the offset is found through that file's own frame table.** A
chunk is intra and sequential, so it would be tempting to compute a frame's
position arithmetically — which is the trap P0 and P1 exist to close, and it is
no more acceptable here for being a small file. Each opened file gets a table
demuxed once and held with its container; the files are short, so it costs
nothing worth measuring and it means one rule covers every seek in the tree.

**Open containers are pooled and few.** Holding one per span would keep a file
handle for every chunk ever written; holding one is a reopen on every drag that
crosses a boundary. Three is what the explorers converged on and it is carried
across rather than re-derived.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from pathlib import Path

import av
import numpy as np

from sieve.frame.table import FrameTable
from sieve.store.coverage import Coverage, Span

#: Files kept open at once. A drag crossing a boundary should not reopen, and a
#: session should not hold a handle per chunk it has ever touched.
OPEN_FILES = 3


class SpanStore:
    """Frames on disk, addressed in rows of the source they came from."""

    def __init__(self, directory: Path, table: FrameTable):
        self.directory = directory
        self.table = table
        self.coverage = Coverage(directory)
        self._open: OrderedDict[str, tuple] = OrderedDict()
        self._lock = threading.RLock()
        self.reads = 0
        self.misses = 0

    # ── reading ──────────────────────────────────────────────────────────
    def fetch(self, form_key: str, row: int) -> np.ndarray | None:
        """The frame at `row` in this form, or `None` if nothing holds it."""
        if not 0 <= row < len(self.table):
            return None
        span = self.coverage.find(form_key, self.table.pts_of(row))
        if span is None:
            self.misses += 1
            return None
        opened = self._container(span)
        if opened is None:
            self.misses += 1
            return None
        container, stream, chunk_table = opened

        start_row = self.table.row_of(span.start_pts)
        if start_row is None:
            # the record points at a pts this source does not have, which
            # means the record belongs to different footage
            self.misses += 1
            return None
        offset = row - start_row
        if not 0 <= offset < len(chunk_table):
            self.misses += 1
            return None

        with self._lock:
            target = chunk_table.pts_of(offset)
            container.seek(target, stream=stream)
            for frame in container.decode(stream):
                if frame.pts is None:
                    continue
                if frame.pts == target:
                    self.reads += 1
                    return self._image(frame)
                if frame.pts > target:
                    break
        self.misses += 1
        return None

    @staticmethod
    def _image(frame) -> np.ndarray:
        plane = frame.planes[0]
        buffer = np.frombuffer(plane, dtype=np.uint8)
        stride = plane.line_size
        view = buffer[: frame.height * stride].reshape(frame.height, stride)
        return np.ascontiguousarray(view[:, : frame.width])

    def _container(self, span: Span):
        with self._lock:
            held = self._open.get(span.filename)
            if held is not None:
                self._open.move_to_end(span.filename)
                return held
            path = self.directory / span.filename
            if not path.exists():
                # recorded but gone: forget it rather than answering absent
                # again on every request for the rest of the session
                self.coverage.forget(span, unlink=False)
                return None
            try:
                container = av.open(str(path))
                stream = container.streams.video[0]
                table = FrameTable.build(path)
            except (OSError, av.FFmpegError, IndexError):
                self.coverage.forget(span)
                return None
            self._open[span.filename] = (container, stream, table)
            while len(self._open) > OPEN_FILES:
                _, (old, _, _) = self._open.popitem(last=False)
                old.close()
            return self._open[span.filename]

    # ── what is here ─────────────────────────────────────────────────────
    def holds(self, form_key: str, row: int) -> bool:
        if not 0 <= row < len(self.table):
            return False
        return self.coverage.find(form_key, self.table.pts_of(row)) is not None

    def rows_held(self, form_key: str) -> list[tuple[int, int]]:
        """Half-open row ranges this store can answer for, in order.

        Rows for a caller's convenience, derived from the pts the record
        actually holds — never the other way round.
        """
        ranges: list[tuple[int, int]] = []
        for span in self.coverage.spans(form_key):
            start = self.table.row_of(span.start_pts)
            if start is not None:
                ranges.append((start, start + span.rows))
        return sorted(ranges)

    def close(self) -> None:
        with self._lock:
            for container, _, _ in self._open.values():
                container.close()
            self._open.clear()

    def release(self, filename: str) -> None:
        """Close one file if it is open, so it can be replaced or deleted."""
        with self._lock:
            held = self._open.pop(filename, None)
        if held is not None:
            held[0].close()
