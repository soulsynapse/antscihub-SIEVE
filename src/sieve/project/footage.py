"""Reading a recording's headers, which is all opening one costs.

What "add a recording" does, and it is deliberately dull: open the container,
read what the headers say, close it. Nothing is moved, nothing is copied, and
nothing is decoded.

**Headers only.** A container's headers give codec, dimensions, frame rate and
duration for the cost of opening the file, and that is everything a card needs.
What this must *not* do is build a frame table: that is a demux of every packet,
seconds per file on the footage this tree runs on
(`docs/findings/2026.08.21-keyframe-index-is-cheap-and-the-gop-is-fixed.md`),
and paying it when somebody has only just pointed at a file would make adding a
recording feel like importing one. The table is built when the recording is
actually opened for work, and cached beside its derived files thereafter.

**Duration, not frames.** A card wants a number and the obvious one is a frame
count, which is exactly the number this footage answers three different ways.
The container's own count is the one that is never right (ADR-0004), so nothing
here reports it; duration is honest, comes free with the headers, and is what
somebody scanning a list is reading for.

**A file that will not open is not an error here.** It is a half-copied
download, or something wearing a video extension that is not one. `read` returns
`None` and the caller says so, because a person who pointed at a file deserves
to be told it could not be read rather than to watch nothing happen.

There is no folder walk in this module and there was in the version before it.
That version existed because a project used to be a folder, and it had to know
which files in one were footage and which were SIEVE's own output — a question
that only arose from the model being wrong. What survives from it, and belongs
here when something needs it, is the *other* detection this tree wants: the
sidecars beside a recording, per `docs/TODO.md`.
"""

from __future__ import annotations

from pathlib import Path

import av

from sieve.frame.shape import Shape
from sieve.project.document import Footage

#: What SIEVE will try to open. A first filter and not a claim — the file still
#: has to open — but it keeps a file dialog's "all files" from costing an
#: `av.open` on a spreadsheet.
VIDEO_SUFFIXES = frozenset({".mp4", ".mkv", ".mov", ".avi", ".m4v", ".mts",
                            ".mpg", ".mpeg", ".webm"})


def looks_like_footage(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_SUFFIXES


def dialog_filter() -> str:
    """The filter a file dialog offers, built from the suffixes above.

    Built rather than written out beside them, because a pair that can disagree
    is one that eventually does — and the way it would fail is a person unable
    to see a file SIEVE would happily have opened.
    """
    patterns = " ".join(f"*{suffix}" for suffix in sorted(VIDEO_SUFFIXES))
    return f"Video ({patterns});;All files (*)"


def read(video: Path) -> Footage | None:
    """One recording's headers, or `None` if it does not open as video."""
    try:
        shape = Shape.read(video)
        with av.open(str(video)) as container:
            stream = container.streams.video[0]
            if stream.duration is not None:
                seconds = float(stream.duration * stream.time_base)
            elif container.duration is not None:
                seconds = container.duration / 1_000_000
            else:
                seconds = 0.0
        stat = video.stat()
    except (OSError, av.FFmpegError, IndexError, ValueError):
        return None
    return Footage(
        name=video.name,
        bytes=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        codec=shape.codec,
        width=shape.width,
        height=shape.height,
        duration_s=seconds,
    )
