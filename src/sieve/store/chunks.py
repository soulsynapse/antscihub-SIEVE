"""Writing a finished span to disk, so the next visit does not re-derive it.

A chunk is the unit of persistence: a fixed run of rows in one form, encoded to
one intra file behind the fill that produced them. Lossy intra rather than
lossless, because that is what
`docs/findings/2026.08.21-lossy-intra-beats-lossless-for-the-cut.md` measured,
and every frame a keyframe because what this file is for is landing on an
arbitrary row without replaying anything.

**Published by rename.** The encoder writes under a temporary name and
`os.replace`s it into position, and only then records the span. Presence in the
record therefore means complete, and the whole apparatus the explorers needed —
trusting a segment once a newer one exists, tracking which file is held open,
deleting a truncated victim after a kill — is not needed for anything this tree
encodes itself. It is still needed for the proxy, where ffmpeg writes the files
and piecewise availability during the run is the point, and it lives there in
one publisher rather than in every reader.

**A chunk is written only when it is whole.** A partial run of rows is not a
smaller chunk, it is a chunk that is not finished; recording it would mean the
record's spans no longer tile and every consumer gains a case. The fill that
produces the frames decides when a run is complete and hands it over in one
piece.
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import av
import numpy as np

from sieve.frame.form import Form
from sieve.frame.table import FrameTable
from sieve.store.coverage import Span, digest
from sieve.store.spans import SpanStore

#: Rows per chunk. Four GOPs of the source, which is what
#: `experiments/storage-experiments/results/02-*` converged on: long enough
#: that the per-file overhead disappears, short enough that a window is tiled
#: by a handful and a partial fill loses little.
CHUNK_ROWS = 96

#: Quality for the stored form. Visually lossless at the level of interest per
#: the lossy-intra finding, and the cost of being wrong here is a re-derive
#: from the original rather than a wrong answer.
CRF = "18"

#: Seconds yielded between encoded frames. A workaround, not a design: the
#: encoder holds the GIL in long stretches and the GUI thread stops breathing.
#: It goes away when encoding moves to a subprocess, the way the proxy builder
#: already runs, and it is named here so that removal is a decision rather than
#: an archaeology problem.
YIELD_S = 0.001


class ChunkStore(SpanStore):
    """A span store that can also produce spans."""

    def __init__(self, directory: Path, table: FrameTable,
                 rows_per_chunk: int = CHUNK_ROWS):
        directory.mkdir(parents=True, exist_ok=True)
        super().__init__(directory, table)
        self.rows_per_chunk = rows_per_chunk
        self.encoded = 0

    def chunk_start(self, row: int) -> int:
        """The first row of the chunk `row` belongs to.

        Chunks sit on an absolute grid rather than on wherever a window began,
        so two windows overlapping the same ground share chunks instead of
        each writing its own copy of the overlap.
        """
        return row - row % self.rows_per_chunk

    def encode(self, form: Form, start_row: int,
               frames: list[np.ndarray]) -> Span | None:
        """Write a completed run of rows, publish it, and record it.

        Returns the recorded span, or `None` if the run could not be written.
        A failure here is a chunk that does not exist, which the next visit
        pays for by re-deriving — never a chunk that exists and is short.
        """
        if not frames:
            return None
        end_row = start_row + len(frames) - 1
        if not (0 <= start_row and end_row < len(self.table)):
            return None

        filename = f"{digest(form.key(), self.table.pts_of(start_row))}.mp4"
        handle, temporary = tempfile.mkstemp(dir=str(self.directory),
                                             suffix=".mp4")
        os.close(handle)
        temporary_path = Path(temporary)
        try:
            self._write(temporary_path, frames)
            self.release(filename)      # a replaced file must not stay open
            os.replace(temporary_path, self.directory / filename)
        except (OSError, av.FFmpegError, ValueError):
            temporary_path.unlink(missing_ok=True)
            return None

        span = Span(form_key=form.key(),
                    start_pts=self.table.pts_of(start_row),
                    end_pts=self.table.pts_of(end_row),
                    rows=len(frames),
                    filename=filename)
        self.coverage.record(span)
        self.encoded += 1
        return span

    def _write(self, path: Path, frames: list[np.ndarray]) -> None:
        """Encode a run of frames, in a format that gives them back unchanged.

        A grey frame is stored as `gray` and never converted to `yuv420p` on
        the way in. That conversion is the obvious one and it is wrong: it
        applies the limited-range convention, so 0 is written as 16 and 255 as
        234, while the read side takes the luma plane raw and does not undo it.
        The round trip is then a contrast squeeze rather than an identity, and
        because both explorers convert this way and read raw, a frame served
        from a persisted chunk differs from the same frame served from memory.
        Nothing reports that: the array has the right shape, the picture looks
        right, and any value computed from it depends on which tier answered.
        It is the hazard `frame.form` states its exact grade to prevent, one
        level lower down.

        Colour is symmetric and needs no such care — `bgr24` in and `bgr24` out
        apply the same convention in both directions — so it converts as
        expected and only the grey path is special.
        """
        colour = frames[0].ndim == 3
        with av.open(str(path), "w") as out:
            stream = out.add_stream("libx264", rate=24)
            stream.height, stream.width = frames[0].shape[:2]
            stream.pix_fmt = "yuv420p" if colour else "gray"
            # g=1: every frame a keyframe, which is what makes landing on an
            # arbitrary row cost one decode instead of replaying a GOP
            stream.options = {"crf": CRF, "preset": "veryfast", "g": "1"}
            for array in frames:
                frame = av.VideoFrame.from_ndarray(
                    array, format="bgr24" if colour else "gray")
                if colour:
                    frame = frame.reformat(format="yuv420p")
                for packet in stream.encode(frame):
                    out.mux(packet)
                if YIELD_S:
                    time.sleep(YIELD_S)
            for packet in stream.encode():
                out.mux(packet)
