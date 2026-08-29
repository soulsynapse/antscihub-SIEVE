"""What can be said about a recording without opening it.

Suffix and size, which cost a stat. The headers — codec, dimensions, frame
rate, duration — are what a card should really say, and they belong to
whichever source tool can open the file rather than here.

**Which files SIEVE will take is not decided here, and was.** A list of
containers is a decoder's opinion, and one sitting in the substrate is
ADR-0009's accretion arriving one reasonable format request at a time: every
lab with a camera writing something ffmpeg does not read is an edit to that
frozenset. The question is now asked of the loaded source tools, through
`sieve.registry` — `source_for` decides, and a tool's `patterns` only hint to
a file chooser.

`kind` survives because a suffix is a filesystem fact and a card has to print
something. It names what the file is called, not what SIEVE can do with it.

What this must not grow is a frame table. Demuxing every packet is seconds per
file on the footage this tree runs on
(`docs/findings/2026.08.21-keyframe-index-is-cheap-and-the-gop-is-fixed.md`),
and paying it when somebody has only just pointed at a file would make adding
a recording feel like importing one.

Nothing here imports Qt.
"""

from __future__ import annotations

from pathlib import Path

_UNITS = ("bytes", "KB", "MB", "GB", "TB")
_STEP = 1024


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
