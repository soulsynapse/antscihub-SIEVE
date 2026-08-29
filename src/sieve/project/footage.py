"""What can be said about a recording without opening it.

Kind and size, which cost a stat. The headers — codec, dimensions, frame
rate, duration — are what a card should really say, and they belong to
whichever source tool can open the file rather than here.

**An address is not a path**, and this assumed one until three sources
disagreed
(`docs/findings/2026.08.29-what-two-more-sources-found-the-contract-cannot-say.md`).
`Source.handles` takes a `str` and the contract never says file: a folder of
stills, a camera and a generator all have addresses. `kind` returned an empty
string for a directory and `size` stated the directory entry — **4 KB for
twelve images**, wrong rather than absent, which is worse. Both now ask what
kind of address they were handed before saying anything about it, and both
answer nothing at all for one that is not on this filesystem. Nothing here
opens anything to find out; that is still a source tool's job.

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


def on_disk(address: str) -> bool:
    """Is this address something this filesystem has?

    A scheme is not, and the checks below would otherwise answer about a path
    that was never meant: `Path("synthetic:frames=40").stat()` asks about a
    file in the working directory whose name happens to contain a colon.
    """
    try:
        return Path(address).exists()
    except OSError:
        return False


def kind(address: str) -> str:
    """What the card calls it: MP4, MKV, MOV — or FOLDER, or the scheme.

    A suffix is a filesystem fact and a card has to print something. It names
    what the address is called, never what SIEVE can do with it.
    """
    scheme, sep, _ = address.partition(":")
    if sep and len(scheme) > 1 and not Path(address).exists():
        # A drive letter is one character, so `C:\...` is not a scheme.
        return scheme.upper()
    path = Path(address)
    if path.is_dir():
        return "FOLDER"
    return path.suffix.lstrip(".").upper()


def size(address: str) -> str:
    """How big it is, or an empty string where that cannot be said.

    A directory is summed over the files directly in it, because the entry's
    own size is an artefact of the filesystem rather than a fact about the
    recording. Not recursive: a source that reads a tree can say so itself,
    and walking somebody's whole archive to draw one card is the cost
    `docs/findings/2026.08.21-keyframe-index-is-cheap-and-the-gop-is-fixed.md`
    refuses at the moment somebody has only just pointed at something.
    """
    path = Path(address)
    try:
        if path.is_dir():
            count = float(sum(entry.stat().st_size
                              for entry in path.iterdir() if entry.is_file()))
        else:
            count = float(path.stat().st_size)
    except OSError:
        return ""
    for unit in _UNITS:
        if count < _STEP or unit == _UNITS[-1]:
            digits = 0 if unit in ("bytes", "KB") else 1
            return f"{count:.{digits}f} {unit}"
        count /= _STEP
    return ""
