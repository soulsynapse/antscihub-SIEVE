"""One container, one position, stepping or seeking to answer.

The software and hardware routes are one class and two constructors, because
they differ in exactly one open option. Two files would have been a copy of a
seek loop, and a seek loop that exists twice is one that gets fixed once.

**Sequential requests step; distant ones seek.** Without that, a play through
this path pays the random-access price per frame — the single largest felt
difference the decode experiments measured. The crossover is `STEP_WITHIN` and
its provenance is stated there.

**The target comes from the frame table, so the match is exact.** Every
predecessor of this code carried a half-frame tolerance to absorb a timestamp it
had computed rather than looked up. With a table there is no residue to absorb:
seek, walk forward, and stop on the pts the table gave. If the walk passes the
target without meeting it, that row decodes to nothing and the answer is `None`
rather than the frame that happened to be next.
"""

from __future__ import annotations

from pathlib import Path

import av
import numpy as np

from sieve.decode.route import STEP_WITHIN
from sieve.frame.form import Form, source_form
from sieve.frame.table import FrameTable


def _plane(frame, index: int, width: int, height: int) -> np.ndarray:
    """One decoded plane as an array, stride and padding removed.

    A plane's rows are `line_size` bytes apart and that is wider than the
    picture, so the buffer is reshaped to the stride and then sliced to the
    width. Reading it as `height * width` instead produces a sheared image that
    still has the right dtype and shape, which is why this is written once.
    """
    buffer = np.frombuffer(frame.planes[index], dtype=np.uint8)
    stride = frame.planes[index].line_size
    return buffer[: height * stride].reshape(height, stride)[:, :width]


class PyAVRoute:
    """A decoder on one file, addressed in rows, delivering the source form."""

    def __init__(self, path: Path, table: FrameTable, *, pix: str = "gray",
                 hwaccel: str | None = None, thread_count: int = 0,
                 step_within: int = STEP_WITHIN):
        options = {}
        if hwaccel:
            from av.codec.hwaccel import HWAccel

            # no software fallback: a hardware route that quietly became a
            # software one would make the seek race unfalsifiable, and the
            # race is the only reason this route is separate at all
            options["hwaccel"] = HWAccel(device_type=hwaccel,
                                         allow_software_fallback=False)
        self.path = path
        self.table = table
        self.hwaccel = hwaccel
        self.step_within = step_within
        self.container = av.open(str(path), **options)
        self.stream = self.container.streams.video[0]
        self.stream.thread_type = "AUTO"
        self.stream.codec_context.thread_count = thread_count
        self.form: Form = source_form(self.stream.width, self.stream.height,
                                      pix)
        self._reformatter = None
        if pix != "gray":
            from av.video.reformatter import VideoReformatter

            # held rather than made per call: the setup is billed each time a
            # reformatter is constructed, which is a per-frame cost pretending
            # to be a conversion cost
            self._reformatter = VideoReformatter()
        self._decoded = None
        self.pos = -1

    # ── pixels ───────────────────────────────────────────────────────────
    def _image(self, frame) -> np.ndarray:
        if self.form.pix == "gray":
            return np.ascontiguousarray(
                _plane(frame, 0, frame.width, frame.height))
        return self._reformatter.reformat(frame, format="bgr24").to_ndarray()

    # ── answering ────────────────────────────────────────────────────────
    def at(self, row: int) -> tuple[np.ndarray, str] | None:
        if not 0 <= row < len(self.table):
            raise IndexError(f"row {row} is outside a table of "
                             f"{len(self.table)}")
        ahead = row - self.pos
        if self._decoded is not None and 0 < ahead <= self.step_within:
            stepped = self._step(ahead)
            if stepped is not None:
                self.pos = row
                return self._image(stepped), f"step x{ahead}"
            # ran off the end of the stream mid-step; a real seek is still
            # entitled to an answer, so fall through rather than reporting none

        target = self.table.pts_of(row)
        self.container.seek(target, stream=self.stream)
        self._decoded = self.container.decode(self.stream)
        for frame in self._decoded:
            if frame.pts is None:
                continue
            if frame.pts == target:
                self.pos = row
                return self._image(frame), "seek"
            if frame.pts > target:
                # walked past it: the packet at that timestamp decoded to
                # nothing, which is a fact about the file and not a failure
                landed = self.table.row_of(int(frame.pts))
                self.pos = landed if landed is not None else -1
                return None
        self.pos = -1
        return None

    def _step(self, ahead: int):
        frame = None
        for _ in range(ahead):
            frame = next(self._decoded, None)
            if frame is None:
                return None
        return frame

    def keyframe_at(self, row: int) -> tuple[np.ndarray, int, str] | None:
        if not 0 <= row < len(self.table):
            raise IndexError(f"row {row} is outside a table of "
                             f"{len(self.table)}")
        target = self.table.pts_of(self.table.keyframe_at_or_before(row))
        self.container.seek(target, stream=self.stream)
        self._decoded = self.container.decode(self.stream)
        for frame in self._decoded:
            if frame.pts is None:
                continue
            landed = self.table.row_of(int(frame.pts))
            if landed is None:
                # a timestamp the table does not carry means the file moved
                # under us, or the seek left the stream we indexed
                continue
            self.pos = landed
            return self._image(frame), landed, f"kf d{row - landed}"
        self.pos = -1
        return None

    def close(self) -> None:
        self.container.close()


def software(path: Path, table: FrameTable, **kwargs) -> PyAVRoute:
    """Threaded software decode — the throughput side of every measurement."""
    return PyAVRoute(path, table, hwaccel=None, **kwargs)


def hardware(path: Path, table: FrameTable, **kwargs) -> PyAVRoute | None:
    """NVDEC, or `None` where there is none.

    `None` rather than an exception: no hardware decoder is an ordinary
    property of a machine, and every caller of this either has a software route
    already or is asking precisely so it can find out.
    """
    try:
        return PyAVRoute(path, table, hwaccel="cuda", **kwargs)
    except Exception:  # noqa: BLE001 - no cuda, no driver, no build support
        return None
