"""What a bake writes, one writer per kind, and what reads it back. Frame kinds go to an H.264
clip through ffmpeg, a table kind to a pickle stream, a signal to a csv. Every writer takes a row
at a time, holds no more than the row it is writing, writes to a part file of its own beside the
target and lands it on close(), and abort() leaves nothing. `reader()` opens a file as the graph
reads a served node: row by row for a frame kind, whole for a series kind. WRITERS says which kinds
have a writer and under what extension, which is what the store answers for."""
import os
import pickle
import shutil
import subprocess
import tempfile

import numpy as np

from .decoder import Decoder

PART = ".part"      # in the name of every file a writer has open and not yet landed; see part()
LOSSLESS, STANDARD = "lossless", "standard"
CRF = "18"          # the standard quality: docs/findings/2026-11-04-remux-encode-and-seek.md's x264 crf 18
PRESET = "medium"
SAID_LINES = 5      # how much of ffmpeg's stderr a failure carries


def ffmpeg():
    return shutil.which("ffmpeg") or "ffmpeg"


def part(path):
    """A new, empty part file beside `path`, named by it and by a token no other writer of the same
    target shares, so two bakes of one key never write the same file."""
    fd, name = tempfile.mkstemp(dir=os.path.dirname(path), prefix=os.path.basename(path) + ".", suffix=PART)
    os.close(fd)
    return name


class ClipWriter:
    """Frames of one kind to an mp4 the video node opens. gray and mask go to yuv420p, full range,
    so a lossless one reads back equal through the decoder's luma path and through BGR alike; a mask
    is always lossless, as 0 and 255; bgr lossless is libx264rgb, exact, and bgr standard yuv420p.
    An odd side is padded by a pixel, since 4:2:0 wants even ones; the sidecar's shape is the true one."""

    def __init__(self, path, kind, fps, quality):
        self.path, self.kind, self.fps = path, kind, float(fps)
        self.quality = LOSSLESS if kind == "mask" else quality
        self.part = part(path)
        self.proc, self.log, self.shape, self.rows, self.bytes = None, None, None, 0, 0

    def command(self, shape):
        h, w = shape[:2]
        pix_in = "bgr24" if self.kind == "bgr" else "gray"
        rate = ["-qp", "0"] if self.quality == LOSSLESS else ["-crf", CRF]
        if self.kind == "bgr" and self.quality == LOSSLESS:
            codec = ["-c:v", "libx264rgb", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2"]
        else:
            codec = ["-c:v", "libx264", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2,scale=in_range=pc:out_range=pc",
                     "-pix_fmt", "yuv420p", "-color_range", "pc"]
        return [ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", pix_in,
                "-s", f"{w}x{h}", "-framerate", f"{self.fps:.6f}", "-i", "-", *codec, *rate, "-preset", PRESET,
                "-an", "-f", "mp4", self.part]

    def write(self, f):
        f = np.asarray(f)
        if f.dtype == bool:
            f = f.astype(np.uint8) * 255
        if self.proc is None:
            self.shape = tuple(int(x) for x in f.shape[:2])
            self.log = open(self.part + ".log", "w+b")
            self.proc = subprocess.Popen(self.command(f.shape), stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self.log)
        elif tuple(f.shape[:2]) != self.shape:
            raise ValueError(f"row {self.rows} is {f.shape[:2]}, the clip {self.shape}")
        self.bytes = f.nbytes
        try:
            self.proc.stdin.write(np.ascontiguousarray(f).tobytes())
        except (BrokenPipeError, OSError):
            raise OSError(f"ffmpeg stopped taking frames: {self._said()}") from None
        self.rows += 1

    def _said(self):
        if self.log is None:
            return ""
        self.log.seek(0)
        return " | ".join(self.log.read().decode(errors="replace").strip().splitlines()[-SAID_LINES:])

    def close(self):
        """Finishes the clip and lands it at `path`; OSError, with ffmpeg's last lines, when it did not encode."""
        if self.proc is None:
            raise OSError("no rows were written")
        self.proc.stdin.close()
        code = self.proc.wait()
        said = self._said()
        self.log.close()
        os.remove(self.log.name)
        if code != 0:
            self.abort()
            raise OSError(f"ffmpeg exited {code}: {said}")
        os.replace(self.part, self.path)
        self.bytes = 0

    def abort(self):
        if self.proc is not None:
            if self.proc.poll() is None:
                self.proc.kill()
                self.proc.wait()
            try:
                self.proc.stdin.close()     # closed here, not by the collector, whose flush of a dead pipe raises
            except OSError:
                pass
        if self.log is not None and not self.log.closed:
            self.log.close()
            os.remove(self.log.name)
        if os.path.exists(self.part):
            os.remove(self.part)
        self.bytes = 0


class _FileWriter:
    """A series kind's writer: rows appended to one file opened at the first write."""

    def __init__(self, path, kind, fps, quality):
        self.path, self.part = path, part(path)
        self.f, self.shape, self.rows, self.bytes = None, None, 0, 0

    def close(self):
        if self.f is None:
            raise OSError("no rows were written")
        self.f.close()
        os.replace(self.part, self.path)
        self.bytes = 0

    def abort(self):
        if self.f is not None and not self.f.closed:
            self.f.close()
        if os.path.exists(self.part):
            os.remove(self.part)
        self.bytes = 0


class TablesWriter(_FileWriter):
    """One table a row, pickled in sequence, the dtype's plane metadata and the contour column with it."""

    def write(self, t):
        if self.f is None:
            self.f = open(self.part, "wb")
            self.shape = (t.dtype.metadata or {}).get("plane")
        pickle.dump(t, self.f, protocol=pickle.HIGHEST_PROTOCOL)
        self.bytes = t.nbytes
        self.rows += 1


def read_tables(path):
    """The tables a TablesWriter wrote, as an object array one table a row."""
    out = []
    with open(path, "rb") as f:
        while True:
            try:
                out.append(pickle.load(f))
            except EOFError:
                break
    rows = np.empty(len(out), object)
    rows[:] = out
    return rows


class SignalWriter(_FileWriter):
    """One value a row, as the shortest text that reads back to the same float32."""

    def write(self, v):
        if self.f is None:
            self.f = open(self.part, "w", encoding="utf-8", newline="\n")
        self.f.write(np.format_float_positional(np.float32(v), trim="-") + "\n")
        self.bytes = 4
        self.rows += 1


def read_signal(path):
    with open(path, encoding="utf-8") as f:
        return np.array([float(line) for line in f if line.strip()], np.float32)


class ClipReader:
    """A baked clip as a served frame node reads it: a Decoder on the file, handing out gray for
    gray and mask kinds, which are written lossless as planes, and bgr for bgr. `shape` is the
    plane's as the bake saved it, and a row is handed out at it, without the pixel the writer padded
    an odd side by; empty, a row is the file's. The decoder's counters are the reader's, for the probe."""

    def __init__(self, path, kind, cache_bytes, shape=()):
        self.decoder = Decoder(path, cache_bytes=cache_bytes)
        self.decoder.output = "bgr" if kind == "bgr" else "gray"
        self.count, self.fps = self.decoder.count, self.decoder.fps
        self.shape = tuple(shape)

    def read(self, row):
        f = self.decoder.read(row)
        if self.shape and f.shape[:2] != self.shape:
            f = np.ascontiguousarray(f[:self.shape[0], :self.shape[1]])
        return f

    def close(self):
        self.decoder.close()


class RowsReader:
    """A baked table file or signal, loaded whole: `data` is the object array of tables or the
    float32 signal, and read(row) one row of it."""

    def __init__(self, path, kind, cache_bytes=0, shape=()):
        self.data = read_signal(path) if kind == "signal" else read_tables(path)
        self.count, self.fps = len(self.data), None

    def read(self, row):
        return self.data[row]

    def close(self):
        pass


def is_series(kind):
    """Whether a bake of `kind` is written whole from the clip walk and read whole, rather than a row at a time."""
    return WRITERS[kind][1] is not ClipWriter


def reader(path, kind, cache_bytes=0, shape=()):
    return (RowsReader if is_series(kind) else ClipReader)(path, kind, cache_bytes, shape)


WRITERS = {"gray": (".mp4", ClipWriter), "bgr": (".mp4", ClipWriter), "mask": (".mp4", ClipWriter),
           "blobs": (".tables", TablesWriter), "tracks": (".tables", TablesWriter), "signal": (".csv", SignalWriter)}
