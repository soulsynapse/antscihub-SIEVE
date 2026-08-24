"""Every frame's timestamp, and the rows that index them.

ADR-0004 implemented. The authoritative identity of a frame is its presentation
timestamp — integer ticks in the stream's own timebase — and a row is a
coordinate into this table and nothing more. Everything durable names a pts;
everything that indexes an array names a row; this module is the only place the
two are converted, and the only place a `Fraction` is handled.

**Built by demuxing, decoding nothing.** Packets carry their timestamps, so the
table costs a read of the file rather than a decode of it — seconds for the
heaviest footage here
(`docs/findings/2026.08.21-keyframe-index-is-cheap-and-the-gop-is-fixed.md`),
which is why it is affordable at open and why it is cached beside the source
rather than rebuilt per session.

**Rows are presentation order, not packet order.** Packets arrive in decode
order, which differs from presentation order wherever the encoder used
out-of-order references, so the table sorts by pts before it hands out row
numbers. A row is therefore "the *n*th frame you would see", which is the only
reading that makes stepping, seeking and a series' row all mean the same thing.

**The table counts packets, and says so.** This footage answers "how many
frames" three ways — metadata, packets, decodable images — and a demux-only pass
can only ever know the second. The leading packets of the 5.3K source decode to
nothing, and that is not discoverable here at any price; a route reports it when
it asks for pixels and gets none. So `len()` is a packet count, deliberately,
and the discrepancy is a decode-time fact rather than a defect in this file.

**Arithmetic is not a substitute for the table.** Computing a pts as
`start + row / rate / timebase` is what this replaces: at a 90 kHz timebase over
23.976 fps a frame is 3753.75 ticks, so the product was never an integer even
before the missing packets, and every consumer that did it carried a half-frame
tolerance to hide the residue. A lookup has no residue and needs no tolerance.
"""

from __future__ import annotations

import json
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import av
import numpy as np


def rescale(pts: int, source: Fraction, target: Fraction) -> int:
    """One stream's ticks expressed in another's timebase.

    Needed because a derived file carries the source's timing but not its
    timebase: ffmpeg preserves *when* a frame is, and the transcode is free to
    express it on a different grid. The arithmetic is exact and only the final
    rounding is not, which is the honest place for the loss — a derived grid
    coarser than the source's genuinely cannot name every source instant, and
    rounding here says so once instead of drifting.
    """
    return round(Fraction(pts) * source / target)


@dataclass(frozen=True)
class FrameTable:
    """Presentation timestamps in row order, and which of them are keyframes."""

    pts: np.ndarray          #: int64, strictly ascending — the real identity
    keyframe: np.ndarray     #: bool, one per row
    timebase: Fraction       #: the stream's own; recorded once, beside them
    start_pts: int           #: the stream's start time, or zero
    duplicate_pts: int = 0   #: packets dropped for repeating a pts already seen

    # ── building ─────────────────────────────────────────────────────────
    @classmethod
    def build(cls, path: Path) -> "FrameTable":
        """Demux every packet of the video stream. Decodes nothing."""
        stamps: list[int] = []
        flags: list[bool] = []
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            timebase = Fraction(stream.time_base)
            start = int(stream.start_time or 0)
            for packet in container.demux(stream):
                # the demuxer emits a final flush packet with no timestamp; a
                # packet that cannot say when it is cannot be given a row
                if packet.pts is None:
                    continue
                stamps.append(int(packet.pts))
                flags.append(bool(packet.is_keyframe))

        order = np.argsort(np.asarray(stamps, dtype=np.int64), kind="stable")
        ordered = np.asarray(stamps, dtype=np.int64)[order]
        keyframes = np.asarray(flags, dtype=bool)[order]
        # a repeated pts would make `row_of` ambiguous and is not a frame the
        # user can ever reach separately, so the first packet claiming an
        # instant keeps it and the count is carried rather than discarded
        if len(ordered):
            first = np.concatenate(([True], np.diff(ordered) != 0))
        else:
            first = np.zeros(0, dtype=bool)
        return cls(
            pts=np.ascontiguousarray(ordered[first]),
            keyframe=np.ascontiguousarray(keyframes[first]),
            timebase=timebase,
            start_pts=start,
            duplicate_pts=int((~first).sum()),
        )

    # ── rows and timestamps ──────────────────────────────────────────────
    def __len__(self) -> int:
        return int(len(self.pts))

    def pts_of(self, row: int) -> int:
        """The timestamp a row is a statement about."""
        return int(self.pts[row])

    def row_of(self, pts: int) -> int | None:
        """The row holding exactly this timestamp, or `None`.

        `None` rather than the nearest row: a caller asking for a specific
        instant that this source does not contain has a real problem, and a
        neighbouring frame returned silently is how a value gets filed against
        a timestamp it was not computed from.
        """
        index = bisect_left(self._as_list, pts)
        if index < len(self.pts) and int(self.pts[index]) == pts:
            return index
        return None

    def row_at_or_before(self, pts: int) -> int | None:
        """The last row at or before a timestamp — where a seek lands."""
        index = bisect_right(self._as_list, pts) - 1
        return index if index >= 0 else None

    def keyframe_at_or_before(self, row: int) -> int:
        """The row a decoder must start from to reach `row`.

        The whole of what a keyframe index buys: a seek's real cost is replaying
        from here, so this is the number a route prices a jump with rather than
        the distance to the frame itself.
        """
        prior = np.flatnonzero(self.keyframe[: row + 1])
        return int(prior[-1]) if len(prior) else 0

    def seconds_of(self, row: int) -> float:
        """A row's position in seconds, for anything that shows a time.

        Returns a float and takes the loss deliberately: a clock readout and a
        slider position want a number they can do ordinary arithmetic on, and
        neither is durable. Nothing that stores anything calls this.
        """
        return float((self.pts_of(row) - self.start_pts) * self.timebase)

    @property
    def timebase_str(self) -> str:
        """The durable spelling, for a sidecar or a record.

        A string because a record is read by things that should not have to
        reconstruct a `Fraction` to know what a tick was worth, and because the
        exact spelling is the point — `1/90000` survives a round trip through
        JSON where a float does not.
        """
        return f"{self.timebase.numerator}/{self.timebase.denominator}"

    @property
    def _as_list(self) -> list[int]:
        # bisect over a numpy array works but compares element-wise through
        # numpy scalars; the list is built once per table and searched many
        # times, which is the trade this property exists to make
        cached = self.__dict__.get("_pts_list")
        if cached is None:
            cached = self.pts.tolist()
            object.__setattr__(self, "_pts_list", cached)
        return cached

    # ── caching ──────────────────────────────────────────────────────────
    def save(self, path: Path, source: Path) -> Path:
        """Write the arrays and a sidecar naming what they are.

        The sidecar carries the source's fingerprint rather than trusting the
        filename, so a table cached beside a file that has since been replaced
        is detected instead of served. Same discipline as a series' sidecar: an
        artifact whose identity has to be recovered by parsing its path stops
        being readable the first time the path cannot hold it.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, pts=self.pts, keyframe=self.keyframe)
        stat = source.stat()
        path.with_suffix(".json").write_text(json.dumps({
            "source": source.name,
            "bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "timebase": self.timebase_str,
            "start_pts": self.start_pts,
            "rows": len(self),
            "keyframes": int(self.keyframe.sum()),
            "duplicate_pts": self.duplicate_pts,
        }, indent=1), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path, source: Path) -> "FrameTable | None":
        """Read a cached table back, or `None` if it does not match `source`.

        Every failure is `None` rather than an exception. A missing, stale or
        corrupt cache means the table gets built, which costs seconds; raising
        would turn a recoverable cost into a session that will not open.
        """
        try:
            meta = json.loads(
                path.with_suffix(".json").read_text(encoding="utf-8"))
            stat = source.stat()
            if (meta["bytes"] != stat.st_size
                    or meta["mtime_ns"] != stat.st_mtime_ns):
                return None
            blob = np.load(path)
            numerator, denominator = meta["timebase"].split("/")
            return cls(
                pts=blob["pts"],
                keyframe=blob["keyframe"],
                timebase=Fraction(int(numerator), int(denominator)),
                start_pts=int(meta["start_pts"]),
                duplicate_pts=int(meta.get("duplicate_pts", 0)),
            )
        except (OSError, ValueError, KeyError):
            return None

    @classmethod
    def cached(cls, source: Path, cache_dir: Path | None = None) -> "FrameTable":
        """The table for a source, built once and read back thereafter."""
        root = cache_dir or source.parent
        path = root / f"{source.stem}.frametable.npz"
        table = cls.load(path, source)
        if table is not None:
            return table
        table = cls.build(source)
        try:
            table.save(path, source)
        except OSError:
            pass  # a read-only footage directory is not a reason to fail
        return table
