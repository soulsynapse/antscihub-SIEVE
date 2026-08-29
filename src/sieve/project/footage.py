"""What can be said about a recording without opening it.

Suffix and size, which cost a stat. The headers — codec, dimensions, frame rate,
duration — cost one container open and are what a card should really say; they
land here when a decoder is a runtime dependency of the application rather than
of the experiments, and until then the library is honest about knowing only what
the filesystem knows.

What this must not grow is a frame table. Demuxing every packet is seconds per
file on the footage this tree runs on
(`docs/findings/2026.08.21-keyframe-index-is-cheap-and-the-gop-is-fixed.md`), and
paying it when somebody has only just pointed at a file would make adding a
recording feel like importing one.

Nothing here imports Qt.
"""

from __future__ import annotations

from pathlib import Path

#: What SIEVE will offer to open. A first filter and not a claim — the file
#: still has to open, which nothing here can yet ask it to do.
VIDEO_SUFFIXES = frozenset(
    {".mp4", ".mkv", ".mov", ".avi", ".m4v", ".mts", ".mpg", ".mpeg", ".webm"}
)

_UNITS = ("bytes", "KB", "MB", "GB", "TB")
_STEP = 1024


def looks_like_footage(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_SUFFIXES


def dialog_filter() -> str:
    """The filter a file dialog offers, built from the suffixes above.

    Built rather than written out beside them, because a pair that can disagree
    is one that eventually does — and the way that failure shows up is somebody
    unable to see a file SIEVE would happily have taken.
    """
    patterns = " ".join(f"*{suffix}" for suffix in sorted(VIDEO_SUFFIXES))
    return f"Video ({patterns});;All files (*)"


def kind(path: Path) -> str:
    """The recording's container as the card says it: MP4, MKV, MOV."""
    return path.suffix.lstrip(".").upper()


def size(path: Path) -> str:
    """How big the file is, or an empty string if it cannot be asked."""
    try:
        count = float(path.stat().st_size)
    except OSError:
        return ""
    for unit in _UNITS:
        if count < _STEP or unit == _UNITS[-1]:
            digits = 0 if unit in ("bytes", "KB") else 1
            return f"{count:.{digits}f} {unit}"
        count /= _STEP
    return ""
