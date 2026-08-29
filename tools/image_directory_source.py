"""The image directory source: frames as separate files in a folder, in name order.

The second source, and it exists to disagree with the first. A protocol written
from one implementation is that implementation wearing an interface's clothes
(`docs/decode/ideas.md`), and every clause in `sieve/contract/edges.py` that the
video file source does not exercise — `Origin.MINTED`, an open `Extent`, a
`FORWARD`-only reach — is a clause nothing has ever read. This tool reads three
of them by being what it is rather than by being contrived.

It is also an ordinary thing an ethologist has: a camera that writes stills, a
tracking package that dumped its frames, a colleague's export.

**Nothing is indexed at open, because there is no index to build.** The video
source demuxes the whole file to name every frame (ADR-0004); here `listdir` is
the frame table, and it is re-read on every `extent()` because a folder being
written into is exactly the non-closed case `Extent`'s own docstring names. That
makes opening cheap and makes the extent a moving target, which is the opposite
shape from a container and the point of having both.

**Positions are minted and the timebase is invented.** Stills carry no
timestamps, so `Origin.MINTED` is honest — but a timebase is required to build a
`Positioning`, and this tool has nothing to build one from. It declares one tick
per image, which orders correctly and lies about time: `Timebase.seconds(4)`
answers `4.0` for the fifth image whatever the interval was. Nothing in the
contract can tell that this is a lie, which is a finding rather than a defect
here, and is written up as one.

**One form for the whole folder, decided by the first image.** `Edge.spec.form`
is fixed at open, so a directory whose images differ in size cannot be described
at all. This tool reports the first image's dimensions and refuses nothing;
mismatched images read back as `None` — listed and not deliverable, which the
contract does have a way to say.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import av
import av.video.reformatter

from sieve.contract import Tool
from sieve.contract.edges import (
    FRAME,
    Access,
    Edge,
    Extent,
    FrameSpec,
    Origin,
    Positioning,
    Timebase,
)
from sieve.contract.forms import source_form
from sieve.contract.nodes import Fingerprint, Opened, Output, Source

#: What this tool will read. libav decodes all of these with no Python imaging
#: library involved, which keeps the tool's dependency the same one the video
#: source already declares.
SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".ppm", ".pgm", ".webp"}
)

#: How many entries `handles` will look at before deciding. A folder of footage
#: sits beside folders of thousands of unrelated files, and answering "is this
#: mine" must not cost a full walk of whatever it was pointed at.
_PEEK = 64


def _stills(folder: Path) -> tuple[Path, ...]:
    """Every image in *folder*, in name order. The frame table, re-read.

    Name order and not modification time: a folder written by a camera is
    already numbered, and mtime reorders itself when somebody copies it.
    """
    try:
        found = [
            entry
            for entry in folder.iterdir()
            if entry.suffix.lower() in SUFFIXES and entry.is_file()
        ]
    except OSError:
        return ()
    return tuple(sorted(found, key=lambda entry: entry.name))


def _decode(path: Path, reformatter: Any) -> Any | None:
    """One image as a BGR array, or None if libav will not read it."""
    try:
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            for frame in container.decode(stream):
                return reformatter.reformat(frame, format="bgr24").to_ndarray()
    except (av.FFmpegError, IndexError, OSError):
        return None
    return None


class _Folder:
    """One open directory. Private to this tool; SIEVE never sees this type."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.stills = _stills(folder)
        if not self.stills:
            raise FileNotFoundError(f"no images in {folder}")
        # One reformatter for the whole folder, for the reason the video source
        # keeps one: `to_ndarray(format=...)` builds and frees an SwsContext per
        # call, which is pure setup on a small frame
        # (`docs/findings/2026.08.21-pyav-to-ndarray-pays-sws-setup-per-call.md`).
        self._reformatter = av.video.reformatter.VideoReformatter()
        first = _decode(self.stills[0], self._reformatter)
        if first is None:
            raise ValueError(f"{self.stills[0].name} did not decode")
        self.height, self.width = first.shape[:2]
        self._first = first

    def extent(self) -> Extent:
        """Asked, not stored — the folder may have grown since the last call.

        Re-listing here is what makes `closed=False` mean something: a caller
        that asks twice and gets two answers is looking at the case the video
        source can never produce.
        """
        self.stills = _stills(self.folder)
        return Extent(tuple(range(len(self.stills))), closed=False)

    def read(self, position: int | None) -> Any | None:
        if position is None:
            raise ValueError("a frame edge is positioned; pass an index")
        if not 0 <= position < len(self.stills):
            raise ValueError(f"{position} is not a frame this source listed")
        frame = _decode(self.stills[position], self._reformatter)
        if frame is None:
            return None
        if frame.shape[:2] != (self.height, self.width):
            # Listed and not deliverable, for a reason a container never has:
            # the folder holds an image of another size, and one form was
            # fixed for all of them at open.
            return None
        return frame

    def fingerprint(self) -> Fingerprint | None:
        """Names and sizes, hashed. Cheap, and it moves when the folder does.

        Deliberately not the pixels: hashing a thousand files to open one is
        the cost the video source refuses for the same reason. The algorithm is
        named in the field so a stabler identity can coexist with this one
        rather than orphan what was written under it.

        This is where an open extent bites. The video source's fingerprint is
        stable because its file is finished; this one answers differently every
        time a still lands, so anything durable filed under it is filed under a
        name that will not be there tomorrow.
        """
        digest = hashlib.sha256()
        for still in self.stills:
            try:
                digest.update(still.name.encode("utf-8"))
                digest.update(str(still.stat().st_size).encode("ascii"))
            except OSError:
                return None
        return Fingerprint("names+sizes/sha256", digest.hexdigest())

    def close(self) -> None:
        self._first = None


def _handles(address: str) -> bool:
    """A directory with at least one image in the first few entries."""
    folder = Path(address)
    if not folder.is_dir():
        return False
    try:
        for seen, entry in enumerate(folder.iterdir()):
            if seen >= _PEEK:
                return False
            if entry.suffix.lower() in SUFFIXES and entry.is_file():
                return True
    except OSError:
        return False
    return False


def _open(address: str) -> Opened:
    folder = Path(address)
    if not folder.is_dir():
        raise NotADirectoryError(f"no directory at {address}")
    state = _Folder(folder)
    edge = Edge(
        # Indexed like the video source's stream, though a folder has only ever
        # one: a name that changes shape between sources is a binding whose
        # meaning depends on which tool answered.
        name="images:0",
        kind=FRAME,
        spec=FrameSpec(source_form(state.width, state.height, "bgr")),
        at=Positioning(
            # One tick per image. There is nothing here to derive a rate from,
            # and the contract requires a timebase to be positioned at all.
            timebase=Timebase(1, 1),
            origin=Origin.MINTED,
            access=Access.RANDOM,
        ),
    )
    return Opened(
        address=address,
        outputs={edge.name: Output(edge=edge, read=state.read,
                                   extent=state.extent)},
        close=state.close,
        fingerprint=state.fingerprint,
    )


TOOLS = (
    Tool(
        name="image directory source",
        #: Bumped when a change here would produce different bytes for one
        #: position — a key over decoded pixels folds it (ADR-0010).
        version=1,
        role=Source(
            handles=_handles,
            open=_open,
            offers=(FRAME,),
            #: A directory has no suffix of its own, so a file chooser built
            #: from patterns cannot offer one. Empty is the honest answer and
            #: costs a click through "All files" — which `Source.patterns`
            #: already says is what a too-narrow pattern costs.
            patterns=(),
        ),
    ),
)
