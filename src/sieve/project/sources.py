"""Finding the footage already in a folder somebody pointed at.

The whole of what "add a project folder" does, and it is deliberately dull:
walk the folder, keep the files that look like video, read their headers, and
write down what was found. Nothing is moved, nothing is copied, and nothing is
decoded.

**Headers only.** A container's headers give codec, dimensions, frame rate and
duration for the cost of opening the file, and that is everything a card needs.
What detection must *not* do is build a frame table: that is a demux of every
packet, seconds per file on the footage this tree runs on
(`docs/findings/2026.08.21-keyframe-index-is-cheap-and-the-gop-is-fixed.md`),
and paying it for every file in a folder somebody has only just pointed at would
make adding a project feel like importing one. The table is built when a source
is actually opened, and cached beside the derived work thereafter.

**Duration, not frames.** A card wants a number and the obvious one is a frame
count, which is exactly the number this footage answers three different ways.
The container's own count is the one that is never right (ADR-0004), so nothing
here reports it; duration is honest, comes free with the headers, and is what
somebody scanning a list is actually reading for.

**A file that cannot be opened is not an error, and is not retried for ever.**
A folder of footage also holds half-copied files, things with a video extension
that are not video, and whatever the camera left behind. Those are skipped and
reported, so a project can say "two files were not readable" rather than failing
to open or pretending it found nothing — and they are *fingerprinted like the
sources are*, because otherwise every scan pays a failed container open for each
of them. One folder in this tree holds fifty-one. A skipped file whose
fingerprint has moved is tried again: a half-copied file that finished copying
is footage now.
"""

from __future__ import annotations

from pathlib import Path

import av

from sieve.frame.shape import Shape
from sieve.project.document import SIEVE_DIR, SourceRecord

#: What counts as footage by its name. A first filter and not a claim — the
#: file still has to open — but it keeps a folder of stills and spreadsheets
#: from costing an `av.open` each.
VIDEO_SUFFIXES = frozenset({".mp4", ".mkv", ".mov", ".avi", ".m4v", ".mts",
                            ".mpg", ".mpeg", ".webm"})

#: Directory names never descended into, whatever a project says. `.sieve`
#: is where a project's own work goes by default; the rest is noise.
SKIP_DIRS = frozenset({SIEVE_DIR, "__pycache__"})


def looks_like_footage(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_SUFFIXES


def walk(folder: Path, ignore: list[Path] | None = None) -> list[Path]:
    """Every candidate file under `folder`, in a stable order.

    Sorted so two scans of one folder agree, and so a project's source list
    does not reshuffle itself between sessions for reasons nobody chose.
    Hidden directories are skipped along with `.sieve`: a dot-directory is
    somebody else's business by convention, and descending into one is how a
    version-control checkout ends up in a project.

    `ignore` is what this particular project has been told not to look in: its
    own derived location, and anything a person excluded. It is passed in
    rather than inferred, because **everything SIEVE produces is a video
    file** — a chunk, a proxy segment and a cut are all `.mp4`, so a detector
    that only knew the name `.sieve` finds them all again as sources of the
    project that made them the moment the derived location is anywhere else.
    Pointed at a folder that had been worked in under an older layout, a
    version of this without `ignore` reported seventy-six sources, of which
    seventy-four were its own output.
    """
    ignored = [p.resolve() for p in (ignore or [])]
    found: list[Path] = []
    for path in sorted(folder.rglob("*")):
        if path.is_dir():
            continue
        parts = path.relative_to(folder).parts[:-1]
        if any(part in SKIP_DIRS or part.startswith(".") for part in parts):
            continue
        resolved = path.resolve()
        if any(resolved == blocked or blocked in resolved.parents
               for blocked in ignored):
            continue
        if looks_like_footage(path):
            found.append(path)
    return found


def read(path: Path, folder: Path) -> SourceRecord | None:
    """One file's record, or `None` if it does not open as video."""
    try:
        shape = Shape.read(path)
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            if stream.duration is not None:
                seconds = float(stream.duration * stream.time_base)
            elif container.duration is not None:
                seconds = container.duration / 1_000_000
            else:
                seconds = 0.0
        stat = path.stat()
    except (OSError, av.FFmpegError, IndexError, ValueError):
        return None
    return SourceRecord(
        path=path.relative_to(folder).as_posix(),
        bytes=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        codec=shape.codec,
        width=shape.width,
        height=shape.height,
        duration_s=seconds,
    )


def stamp(path: Path, folder: Path) -> SourceRecord | None:
    """A record with a fingerprint and no headers: what a skip remembers."""
    try:
        stat = path.stat()
    except OSError:
        return None
    return SourceRecord(path=path.relative_to(folder).as_posix(),
                        bytes=stat.st_size, mtime_ns=stat.st_mtime_ns)


def detect(folder: Path,
           known: list[SourceRecord] | None = None,
           ignore: list[Path] | None = None,
           skipped: list[SourceRecord] | None = None
           ) -> tuple[list[SourceRecord], list[SourceRecord]]:
    """What footage is in `folder` now, and what would not open.

    `known` and `skipped` are what the project recorded last time. A file
    whose fingerprint still matches either list is carried over rather than
    re-opened, so re-detecting a folder of a hundred files costs a `stat`
    each rather than a hundred container opens — and a folder of unreadable
    leftovers costs a `stat` each rather than a hundred *failed* opens,
    which was the version that made a rescan of a worked-in folder slow.
    A file that has changed is read again either way, which is the point of
    fingerprinting it in the first place.
    """
    previous = {record.path: record for record in (known or [])}
    refused = {record.path: record for record in (skipped or [])}
    records: list[SourceRecord] = []
    unreadable: list[SourceRecord] = []
    for path in walk(folder, ignore):
        relative = path.relative_to(folder).as_posix()
        carried = previous.get(relative)
        if carried is not None and carried.matches(folder):
            records.append(carried)
            continue
        remembered = refused.get(relative)
        if remembered is not None and remembered.matches(folder):
            unreadable.append(remembered)
            continue
        fresh = read(path, folder)
        if fresh is None:
            mark = stamp(path, folder)
            if mark is not None:
                unreadable.append(mark)
            continue
        records.append(fresh)
    return records, unreadable
