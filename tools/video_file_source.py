"""The video file source: frames off a container on disk, decoded with PyAV.

The first tool, and the one that proves the boundary: SIEVE holds no list of
containers, no decoder, and no opinion about how frames come out of a file.
All of it is here, where somebody who disagrees can replace it.

**The frame table is built by demuxing and decoding nothing** (ADR-0004).
Packets carry timestamps, so one pass names every frame the file claims —
seconds on the heaviest footage in this tree, paid once at open
(`docs/findings/2026.08.21-keyframe-index-is-cheap-and-the-gop-is-fixed.md`).
The same pass collects keyframes, which is what makes the seek decision below
possible.

**Listed is not deliverable, and this is where that is real.**
`video-tests/GX010047c2_02_17_26.MP4` was cut mid-GOP before SIEVE saw it, so
its leading packets have timestamps and decode to nothing. Those are listed
and read back as `None`.

**Conversion goes through one reused reformatter.** `frame.to_ndarray(format=
...)` builds and frees an SwsContext per call — 49x of pure setup on a small
frame, still 1.4x on a 5.3K one
(`docs/findings/2026.08.21-pyav-to-ndarray-pays-sws-setup-per-call.md`).

**Forward decoding beats seeking within about a GOP**, since a seek costs a
GOP and not a frame
(`docs/findings/2026.08.21-uncut-seek-costs-a-gop-not-a-frame.md`). The GOP
length is measured off this file's own keyframes rather than assumed.

Not done here yet, deliberately: building a proxy or a cut. Those dominate
everything else on the decode shelf, and a source that quietly makes one is
spending time the substrate cannot account for (ADR-0008).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from statistics import median
from typing import Any

import av
import av.video.reformatter
import numpy as np

from sieve.contract import Tool
from sieve.contract.edges import (
    FRAME,
    Access,
    Edge,
    Extent,
    Origin,
    Positioning,
    Timebase,
)
from sieve.contract import forms
from sieve.contract.forms import Form, source_form
from sieve.contract.nodes import (
    Answer,
    Fingerprint,
    Opened,
    Output,
    Refusal,
    Source,
)

#: What this tool will try. SIEVE holds no such list on purpose — a list of
#: containers is a decoder's opinion, and one in the substrate is ADR-0009's
#: accretion arriving one reasonable format request at a time.
SUFFIXES = frozenset(
    {".mp4", ".mkv", ".mov", ".avi", ".m4v", ".mts", ".mpg", ".mpeg", ".webm"}
)

#: Fingerprint block size, both ends: two seeks and a stat, so verifying on
#: open is free and testing a folder of candidates stays under a second.
_BLOCK = 64 * 1024

#: Used when a file has too few keyframes to measure a GOP from.
_GOP_FALLBACK = 30


class _VideoFile:
    """One opened file. Private to this tool; SIEVE never sees this type."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.listed, self.keyframes = _table(path)
        #: pts to its place in the listing. The seek decision is a distance in
        #: *frames* and a pts difference is not one: at 90 kHz over 23.976 fps
        #: one frame is 3753.75 ticks, and comparing that against a GOP length
        #: of 24 makes every step look like a jump of forty GOPs.
        self._rank = {pts: index for index, pts in enumerate(self.listed)}
        self._present = frozenset(self.listed)
        self._gop = _gop_length(self.listed, self.keyframes)

        self._container = av.open(str(path))
        self._stream = self._container.streams.video[0]
        self._stream.thread_type = "AUTO"
        self._reformatter = av.video.reformatter.VideoReformatter()
        self._frames: Any = None
        self._cursor: int | None = None

    def extent(self) -> Extent:
        return Extent(self.listed, closed=True)

    def starts(self) -> tuple[int, ...]:
        """The keyframes, which the same demux pass already collected.

        A caller landing on one of these decodes a single packet; landing
        between them decodes forward from the last one, and landing *before*
        the first decodes nothing at all, which is what the cut-away GOP at
        the head of `video-tests/GX010047c2_02_17_26.MP4` is. Handing the list
        over is how somebody finds that out without paying a seek per frame to
        be refused.
        """
        return self.keyframes

    def read(self, position: int | None, want: Form) -> Answer:
        """A frame at *position*, cropped here when the caller wants less.

        The crop is the cheap half and it is taken: returning the whole 5.3K
        picture when a 1024-square region was asked for is 47.6 MB held where
        1 MB was wanted, and the tier stack this feeds never held more.

        **Gray is served from plane 0, and that is the settled answer.** This
        decoder's luma and BT.601 over the decoded BGR are different
        quantities, and the one that is backed by measurement is the plane:
        the session explorer took it, and every number on the storage shelf —
        the ~120 fps sequential fill, the cut, the tuning loop — was measured
        on frames that came out that way. The BT.601 construction was written
        from argument and never run. Refusing gray here to send it to that
        construction cost the whole 5.3K BGR reformat before a 1024-square
        crop: 18.7 ms a frame against the plane's ~8, on a path where the
        crop was supposed to be the cheap half.
        """
        if position is None:
            raise ValueError("a frame edge is positioned; pass a pts")
        if position not in self._present:
            raise ValueError(f"{position} is not a frame this source listed")
        source = source_form(self._stream.codec_context.width,
                             self._stream.codec_context.height, "bgr")
        if not want.native or forms.grade(source, want) is None:
            return Answer(refusal=Refusal.FORM)
        ahead = (
            None
            if self._cursor is None
            else self._rank.get(position, -1) - self._rank.get(self._cursor, -1)
        )
        if (
            self._frames is None
            or ahead is None
            # At the cursor as well as behind it: the cursor names the frame
            # already handed out, so asking for it again needs a seek too.
            or ahead <= 0
            # In frames, which is what a GOP is measured in. Comparing the pts
            # difference here made every sequential step read as a jump and
            # seek, at ~289 ms a frame where decoding on costs about five
            # (`docs/findings/2026.08.21-uncut-seek-costs-a-gop-not-a-frame.md`).
            or ahead > self._gop
        ):
            self._seek(position)
        while True:
            try:
                frame = next(self._frames)
            except (StopIteration, av.FFmpegError):
                self._frames, self._cursor = None, None
                return Answer(refusal=Refusal.GONE)
            if frame.pts is None:
                continue
            self._cursor = frame.pts
            if frame.pts == position:
                if want.pix == "gray":
                    # No reformatter on this path at all: the plane is already
                    # the wanted format, so a crop is a slice of it and the
                    # 47.6 MB colour conversion never happens. `forms.build`
                    # still does the cropping — the rect and the sampling stay
                    # the contract's, only the pixels are the decoder's.
                    return Answer(forms.build(_plane(frame), want))
                whole = self._reformatter.reformat(
                    frame, format="bgr24"
                ).to_ndarray()
                if want != source:
                    return Answer(forms.build(whole, want))
                # Contiguous, even on the path that shapes nothing. A decoder
                # pads its rows to its own alignment, so `to_ndarray` on a
                # width whose bytes are not a multiple of it hands back a
                # strided view: 462 px is 1386 bytes of picture in a 1392-byte
                # row on `video-tests/rep3_intermittent_crop.MP4`. Every
                # consumer of a frame wants one buffer — Qt refuses to wrap a
                # strided array and an encoder refuses to take one — and
                # `forms.build` already normalises, so this is the one exit
                # that did not. A no-op where the width happens to align.
                return Answer(np.ascontiguousarray(whole))
            if frame.pts > position:
                # The decoder went past it — what a packet that decodes to
                # nothing looks like from out here. GONE and not LATER: this
                # file is finished, so the packet will never decode, and a
                # caller that keeps asking pays a seek each time to be told.
                return Answer(refusal=Refusal.GONE)

    def fingerprint(self) -> Fingerprint | None:
        """Size with a checksum of the first and last block.

        The algorithm is named in the field so a content-level fingerprint can
        one day coexist with this one rather than orphan what was written under
        it; `docs/architecture-leads.md` carries the argument.

        Byte identity, not content identity: a lossless remux decodes to the
        same frames and fingerprints differently, so this calls it a different
        recording where a person would not. That direction is deliberate — a
        false alarm asks a question, the alternative accepts the wrong file.
        """
        try:
            size = self.path.stat().st_size
            digest = hashlib.sha256()
            with self.path.open("rb") as handle:
                digest.update(handle.read(_BLOCK))
                if size > _BLOCK:
                    handle.seek(max(0, size - _BLOCK))
                    digest.update(handle.read(_BLOCK))
        except OSError:
            return None
        return Fingerprint(f"size+edges/sha256/{_BLOCK}",
                           f"{size:x}:{digest.hexdigest()}")

    def close(self) -> None:
        self._frames = None
        container, self._container = self._container, None
        if container is not None:
            container.close()

    def _seek(self, position: int) -> None:
        self._container.seek(
            max(position, 0), stream=self._stream, backward=True, any_frame=False
        )
        self._frames = self._container.decode(self._stream)
        self._cursor = None


def _plane(frame) -> Any:
    """Plane 0 as a height-by-width view, with the decoder's padding dropped.

    A plane's rows are `line_size` wide and the picture is the left `width` of
    each — slicing that off is what makes the result an array of the shape the
    form names rather than one with a stride nobody downstream asked about.
    """
    plane = frame.planes[0]
    flat = np.frombuffer(plane, dtype=np.uint8)[: frame.height * plane.line_size]
    return flat.reshape(frame.height, plane.line_size)[:, : frame.width]


def _handles(address: str) -> bool:
    path = Path(address)
    return path.suffix.lower() in SUFFIXES and path.is_file()


def _open(address: str) -> Opened:
    path = Path(address)
    if not path.is_file():
        raise FileNotFoundError(f"no file at {address}")
    state = _VideoFile(path)
    stream = state._stream
    base = stream.time_base
    edge = Edge(
        # Indexed always, never bare "video": a name that changes when a
        # second stream appears is a binding that breaks silently.
        name=f"video:{stream.index}",
        kind=FRAME,
        form=source_form(stream.codec_context.width,
                         stream.codec_context.height, "bgr"),
        at=Positioning(
            timebase=Timebase(base.numerator, base.denominator),
            origin=Origin.CARRIED,
            access=Access.RANDOM,
        ),
    )
    return Opened(
        address=address,
        outputs={edge.name: Output(edge=edge, read=state.read,
                                   extent=state.extent, starts=state.starts)},
        close=state.close,
        fingerprint=state.fingerprint,
    )


def _table(path: Path) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Every packet's pts and every keyframe's, decoding nothing."""
    listed: list[int] = []
    keyframes: list[int] = []
    container = av.open(str(path))
    try:
        stream = container.streams.video[0]
        for packet in container.demux(stream):
            if packet.pts is None:
                continue          # the flush packet that ends a demux
            listed.append(packet.pts)
            if packet.is_keyframe:
                keyframes.append(packet.pts)
    finally:
        container.close()
    return tuple(sorted(listed)), tuple(sorted(keyframes))


def _gop_length(listed: tuple[int, ...], keyframes: tuple[int, ...]) -> int:
    """How many frames a seek would decode through.

    Measured off this file rather than assumed: the number decides whether a
    request ahead of the cursor is served by decoding on or by paying a seek,
    and it differs by an order of magnitude between an intra-only
    intermediate and a long-GOP original.
    """
    if len(keyframes) < 2 or not listed:
        return _GOP_FALLBACK
    rank = {pts: i for i, pts in enumerate(listed)}
    steps = [rank[b] - rank[a] for a, b in zip(keyframes, keyframes[1:])
             if a in rank and b in rank]
    return max(1, int(median(steps))) if steps else _GOP_FALLBACK


TOOLS = (
    Tool(
        name="video file source",
        #: Bumped when a change here would produce different bytes for one
        #: position — a key over decoded pixels folds it (ADR-0010). 2: gray
        #: is the decoder's luma plane, where it was BT.601 over the decoded
        #: BGR. Every gray array this tool has ever produced is superseded.
        version=2,
        role=Source(
            handles=_handles,
            open=_open,
            #: A container decodes to pixels and to nothing else. Declared, not
            #: a version-bearing fact: this says what kind of thing comes out,
            #: never what the bytes are, so ADR-0010's key does not fold it.
            offers=(FRAME,),
            patterns=tuple(f"*{suffix}" for suffix in sorted(SUFFIXES)),
        ),
    ),
)
