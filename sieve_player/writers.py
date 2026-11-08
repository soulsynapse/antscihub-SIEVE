"""What a bake writes, one writer per kind: frame kinds to an H.264 clip through ffmpeg, a table
kind to a pickle stream, a signal to a csv. Every writer takes a row at a time, holds no more than
the row it is writing, writes to a .part beside the target and lands it on close(), and abort()
leaves nothing; `read_tables` and `read_signal` read the last two back. WRITERS says which kinds
have one and under what extension, which is what the store answers for."""
import os
import pickle
import shutil
import subprocess

import numpy as np

LOSSLESS, STANDARD = "lossless", "standard"
CRF = "18"          # the standard quality: docs/findings/2026-11-04-remux-encode-and-seek.md's x264 crf 18
PRESET = "medium"


def ffmpeg():
    return shutil.which("ffmpeg") or "ffmpeg"


class ClipWriter:
    """Frames of one kind to an mp4 the video node opens. gray and mask go to yuv420p, full range,
    so a lossless one reads back equal through the decoder's luma path and through BGR alike; a mask
    is always lossless, as 0 and 255; bgr lossless is libx264rgb, exact, and bgr standard yuv420p.
    An odd side is padded by a pixel, since 4:2:0 wants even ones; the sidecar's shape is the true one."""

    def __init__(self, path, kind, fps, quality):
        self.path, self.kind, self.fps = path, kind, float(fps)
        self.quality = LOSSLESS if kind == "mask" else quality
        self.part = path + ".part"
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
        return self.log.read().decode(errors="replace").strip().splitlines()[-1:] or ""

    def close(self):
        """Finishes the clip and lands it at `path`; OSError, with ffmpeg's last line, when it did not encode."""
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


class TablesWriter:
    """One table a row, pickled in sequence, the dtype's plane metadata and the contour column with it."""

    def __init__(self, path, kind, fps, quality):
        self.path, self.part = path, path + ".part"
        self.f, self.shape, self.rows, self.bytes = None, None, 0, 0

    def write(self, t):
        if self.f is None:
            self.f = open(self.part, "wb")
            self.shape = (t.dtype.metadata or {}).get("plane")
        pickle.dump(t, self.f, protocol=pickle.HIGHEST_PROTOCOL)
        self.bytes = t.nbytes
        self.rows += 1

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


class SignalWriter:
    """One value a row, as the shortest text that reads back to the same float32."""

    def __init__(self, path, kind, fps, quality):
        self.path, self.part = path, path + ".part"
        self.f, self.shape, self.rows, self.bytes = None, None, 0, 0

    def write(self, v):
        if self.f is None:
            self.f = open(self.part, "w", encoding="utf-8", newline="\n")
        self.f.write(np.format_float_positional(np.float32(v), trim="-") + "\n")
        self.bytes = 4
        self.rows += 1

    close, abort = TablesWriter.close, TablesWriter.abort


def read_signal(path):
    with open(path, encoding="utf-8") as f:
        return np.array([float(line) for line in f if line.strip()], np.float32)


WRITERS = {"gray": (".mp4", ClipWriter), "bgr": (".mp4", ClipWriter), "mask": (".mp4", ClipWriter),
           "blobs": (".tables", TablesWriter), "tracks": (".tables", TablesWriter), "signal": (".csv", SignalWriter)}
