"""Building the display proxy in pieces, nearest to attention first.

Two halves that must not be one. **The schedule is a pure function** — given
which segments exist, how many there are, and where attention is, it says which
batch to build next — and it is a list a check can compare against. **The
builder is the impure half**: it launches a process, watches it, publishes what
it finishes, and kills it when attention moves far enough. The explorer has both
inside one class with a subprocess handle, which is why its order has never been
asserted, only felt.

What the schedule encodes, from
`experiments/storage-experiments/results/06-build-order-*.json`: batches rather
than one linear pass, because process creation is expensive enough on Windows to
be worth amortising and a batch of four costs a few percent of wall over one
pass while making position free; ordered by distance from attention, so the part
of the timeline somebody is looking at gets fast first; redirected when a
landing commits far from the batch in flight, but only when there is nearer work
to do; and resuming across sessions for nothing, because the schedule is only
ever *whichever batches are missing, nearest first* and a directory of finished
segments is the entire state.

**Never while a fill is running.** The two would be reading the same original
through two decoders, and software decoders collapse under contention
(`docs/findings/2026.08.21-software-decoders-collapse-under-contention.md`).
Attention first: the window somebody landed in gets the decoder, and the proxy
waits.

**Published by rename, which is not free here.** Anything this tree encodes
itself is written to a temporary name and renamed, so presence means complete
(`sieve.store.chunks`). ffmpeg writes its own segment files and the point of
segmenting is that each is usable the moment it is finished, so the builder
cannot simply rename at the end. Instead a segment is published — moved from the
staging directory into place and recorded — once the *next* one appears, which
is the evidence ffmpeg has moved past it, and the last of a batch is published
when the process exits. The heuristic survives; what changes is that it lives in
one publisher instead of being spread across every reader.
"""

from __future__ import annotations

import os
import subprocess
import threading
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Protocol

from sieve.frame.form import Form
from sieve.frame.shape import Shape
from sieve.frame.table import FrameTable
from sieve.store.coverage import Span
from sieve.store.spans import SpanStore

#: Segments per invocation. One pass is marginally cheaper in wall time and
#: gives up ordering entirely; four buys attention-ordering for a few percent
#: (`experiments/storage-experiments/results/06-build-order-*.json`).
BATCH = 4

#: How far attention must move, in segments, before a batch in flight is worth
#: abandoning. Below this the batch finishes; above it, and only when there is
#: nearer work, it is killed and restarted where somebody is looking.
REDIRECT = 8

#: How wide a display form is, everywhere. One figure and not two, because
#: a form is its key: if the proxy were built at one width and the loop
#: played at another, a finished proxy segment could never answer the thing
#: that plays — same instant, same source pixels, two keys, two pictures.
#:
#: A stated number and never a measured one. It must not come from the
#: canvas, the pane or the window: `frame.form.Form.key` says a key may name
#: none of those because a form outlives all three, and ADR-0005 names
#: window size among the things a recorded set may not depend on. Sizing a
#: stored form to the geometry it happened to be drawn at would make two
#: runs of one recording produce keys that cannot be matched.
#:
#: The value is the width the decode experiments ran their display-size
#: comparisons at, and moving it is a decision about what a display form
#: *is* — every chunk and segment already written at the old one stops
#: answering, honestly, because it is a different picture.
DISPLAY_WIDTH = 1328


def display_size(width: int, height: int,
                 target: int = DISPLAY_WIDTH) -> tuple[int, int]:
    """What a source of `width` by `height` becomes at display sampling.

    One function, and everything that needs the answer calls it. `scale=W:-2`
    keeps the aspect and rounds the free dimension to the *nearest* even
    number, which is not the same as truncating to an even number and differs
    by two often enough to matter — on the source in `video-tests/` the two
    rules give 748 and 746.

    This exists because that difference has now been written twice. The first
    time, a proxy was recorded as `1328x746` while ffmpeg had written
    `1328x748`, and the record described frames the store did not hold. The fix
    was to expose the launcher's own arithmetic and a comment saying to ask it
    — which held exactly until somebody who could not reach a launcher needed
    the same answer and worked it out again. A rule that lives in a comment is
    a rule with as many implementations as it has readers, so it lives here.
    """
    # never wider than the source. A display form is a *reduction*, and a
    # proxy built above the source it came from stores more pixels than it
    # was given and invents none of them — the 462-wide recording in
    # video-tests/ would have been upscaled to 1328, nearly three times
    # larger than the thing it is a cheap copy of. The clamp lives here
    # because it lived in one of the two callers and not the other, which
    # is how they came to disagree.
    target = max(2, min(target, width))
    scaled = max(2, round(height * target / width / 2) * 2)
    return target, scaled


@dataclass(frozen=True)
class Batch:
    """A run of segment indices to build in one invocation."""

    start: int
    count: int

    @property
    def centre(self) -> float:
        return self.start + self.count / 2

    def distance_from(self, attention: int) -> float:
        return abs(attention - self.centre)

    def __iter__(self):
        return iter(range(self.start, self.start + self.count))


# ── the schedule: pure, and therefore assertable ─────────────────────────
def missing_batches(present: set[int], expected: int,
                    batch: int = BATCH) -> list[Batch]:
    """Every batch with at least one segment still to build, in index order."""
    out: list[Batch] = []
    for start in range(0, expected, batch):
        count = min(batch, expected - start)
        if any(index not in present for index in range(start, start + count)):
            out.append(Batch(start, count))
    return out


def next_batch(present: set[int], expected: int, attention: int,
               batch: int = BATCH) -> Batch | None:
    """The batch to build now: the nearest unfinished one to attention.

    Ties break towards the lower index so that two runs from one state build
    in the same order — a schedule that depended on set iteration would make
    a resumed session's order unreproducible for no reason.
    """
    remaining = missing_batches(present, expected, batch)
    if not remaining:
        return None
    return min(remaining, key=lambda b: (b.distance_from(attention), b.start))


def should_redirect(running: Batch, attention: int, present: set[int],
                    expected: int, batch: int = BATCH,
                    threshold: int = REDIRECT) -> bool:
    """Is the batch in flight far enough from attention to be worth killing?

    Two conditions, and the second is the one that keeps this from thrashing:
    attention must be further than `threshold` from the running batch, *and*
    there must be unfinished work nearer than that. A redirect with nothing
    nearer to go to throws away a batch in progress to start an equally
    distant one.
    """
    here = running.distance_from(attention)
    if here <= threshold:
        return False
    remaining = [b for b in missing_batches(present, expected, batch)
                 if b.start != running.start]
    return any(b.distance_from(attention) < here for b in remaining)


# ── the launcher: the impure half, injectable so the schedule can be checked ──
class Launcher(Protocol):
    """Whatever actually produces segment files."""

    def launch(self, batch: Batch, staging: Path): ...
    def poll(self, handle) -> int | None: ...
    def terminate(self, handle) -> None: ...


class FFmpegLauncher:
    """One ffmpeg per batch, segmenting on the absolute grid as it goes.

    `-g 1` makes every frame a keyframe, which is both what the proxy is for
    and what lets `-segment_frames` split exactly on the grid. A resumed
    build's `-ss` is frame-accurate to half a frame early, so the first frame
    emitted is exactly the batch's first row.
    """

    def __init__(self, source: Path, shape: Shape, rows: int,
                 rows_per_segment: int, width: int = DISPLAY_WIDTH):
        self.source = source
        self.shape = shape
        self.rows = rows
        self.rows_per_segment = rows_per_segment
        self.width = width

    def output_size(self) -> tuple[int, int]:
        """The dimensions ffmpeg will actually write.

        Deferred to `display_size` rather than worked out here: the same answer
        is wanted by anything that plays a display form, and the last time this
        arithmetic existed in two places the two disagreed by two pixels and
        produced two keys for one picture.
        """
        return display_size(self.shape.width, self.shape.height, self.width)

    def form(self) -> Form:
        """The form this launcher's output actually is.

        Ask the launcher rather than working it out: a caller that computes
        the geometry itself is a second implementation of ffmpeg's rounding,
        and the two disagreeing is silent.
        """
        return Form((0, 0, self.shape.width, self.shape.height),
                    self.output_size(), "gray")

    def launch(self, batch: Batch, staging: Path):
        staging.mkdir(parents=True, exist_ok=True)
        first_row = batch.start * self.rows_per_segment
        wanted = min(batch.count * self.rows_per_segment,
                     self.rows - first_row)
        command = ["ffmpeg", "-y"]
        if first_row:
            seconds = float((Fraction(first_row) - Fraction(1, 2))
                            / self.shape.average_rate)
            command += ["-ss", f"{seconds:.6f}"]
        command += ["-i", str(self.source),
                    "-vf", f"scale={self.width}:-2",
                    "-c:v", "libx264", "-crf", "23", "-preset", "veryfast",
                    "-g", "1", "-fps_mode", "passthrough", "-an",
                    "-frames:v", str(wanted)]
        splits = ",".join(str(row) for row in
                          range(self.rows_per_segment, wanted,
                                self.rows_per_segment))
        if splits:
            command += ["-f", "segment", "-segment_frames", splits,
                        "-reset_timestamps", "1",
                        "-segment_start_number", str(batch.start),
                        str(staging / "seg-%05d.mp4")]
        else:
            command += [str(staging / f"seg-{batch.start:05d}.mp4")]
        # below normal: the proxy is the thing that may always wait
        flags = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
        return subprocess.Popen(command, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, creationflags=flags)

    def poll(self, handle) -> int | None:
        return handle.poll()

    def terminate(self, handle) -> None:
        handle.terminate()
        handle.wait()


# ── the builder: schedule plus launcher plus publication ─────────────────
class ProxyBuilder:
    """Runs the schedule, and publishes what the launcher finishes."""

    def __init__(self, store: SpanStore, table: FrameTable, form_key: str,
                 launcher: Launcher, segments: int, rows_per_segment: int,
                 # `form_key` must be the launcher's own `form().key()` where
                 # the launcher has one. Passing a key computed anywhere else
                 # records a description of frames this store does not hold.
                 batch: int = BATCH, redirect: int = REDIRECT):
        self.store = store
        self.table = table
        self.form_key = form_key
        self.launcher = launcher
        self.segments = segments
        self.rows_per_segment = rows_per_segment
        self.batch = batch
        self.redirect = redirect
        self.staging = store.directory / "_staging"
        self.attention = 0
        self.running: Batch | None = None
        self.handle = None
        self.published = 0
        self.redirects = 0
        self._launching = False
        self._stopped = False
        self._lock = threading.RLock()

    # ── what exists ──────────────────────────────────────────────────────
    def present(self) -> set[int]:
        """Segments finished and recorded. The whole of the resumable state."""
        held = set()
        for start, end in self.store.rows_held(self.form_key):
            held.add(start // self.rows_per_segment)
        return held

    def done(self) -> bool:
        with self._lock:
            return (not self._launching and self.handle is None
                    and not missing_batches(self.present(), self.segments,
                                            self.batch))

    # ── driving it ───────────────────────────────────────────────────────
    def commit(self, row: int) -> None:
        """Attention landed somewhere. Redirect if it is worth it."""
        with self._lock:
            self.attention = row // self.rows_per_segment
            if self.handle is None or self.running is None:
                return
            if self.launcher.poll(self.handle) is not None:
                return
            if should_redirect(self.running, self.attention, self.present(),
                               self.segments, self.batch, self.redirect):
                self._kill()
                self.redirects += 1

    def tick(self, fill_running: bool = False) -> bool:
        """Advance the schedule. True while a batch is in flight."""
        with self._lock:
            if self._launching:
                return True
            if self.handle is not None:
                # polled once and remembered. Asking twice is not merely
                # wasteful: whether the process has exited is exactly what
                # decides if the last segment of the batch may be published,
                # so two answers in one tick means publishing against one and
                # branching on the other. A version of this polled before
                # publishing and again to branch, so the final segment of
                # every batch was held back forever, the batch never completed,
                # and the schedule relaunched it for the rest of the session.
                exited = self.launcher.poll(self.handle) is not None
                self._publish(finished=exited)
                if not exited:
                    return True
                self.handle = None
                self.running = None
            if fill_running:
                # attention first: never race a fill for the original, or
                # both decoders collapse and the window somebody is actually
                # looking at is the one that suffers
                return False
            batch = next_batch(self.present(), self.segments, self.attention,
                               self.batch)
            if batch is None:
                return False
            self.running = batch
            self._launching = True

        def spawn():
            handle = self.launcher.launch(batch, self.staging)
            with self._lock:
                if self._stopped:
                    self.launcher.terminate(handle)
                    self._launching = False
                    return
                self.handle = handle
                self._launching = False

        # process creation blocks for hundreds of milliseconds on Windows and
        # has been measured far worse; it does not belong on a caller's thread
        threading.Thread(target=spawn, daemon=True).start()
        return True

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
            if self.handle is not None:
                self._kill()

    def _kill(self) -> None:
        self.launcher.terminate(self.handle)
        self.handle = None
        # publish whatever is complete, then discard the one being written:
        # a truncated segment that reached the store would serve short and
        # nothing downstream could tell
        self._publish(finished=False)
        for path in self.staging.glob("seg-*.mp4"):
            path.unlink(missing_ok=True)
        self.running = None

    # ── publication ──────────────────────────────────────────────────────
    def _publish(self, finished: bool) -> int:
        """Move finished segments out of staging and record them.

        A segment is finished once a later one exists, because that is the
        evidence ffmpeg has moved past it, or once the process has exited. The
        heuristic is unavoidable — ffmpeg writes these files and the point of
        segmenting is that each is usable before the run ends — and it is
        confined to this method so that no reader has to know about it.
        """
        if not self.staging.is_dir():
            return 0
        found = sorted(int(p.stem.split("-")[1])
                       for p in self.staging.glob("seg-*.mp4"))
        if not found:
            return 0
        ready = found if finished else found[:-1]
        moved = 0
        for index in ready:
            source = self.staging / f"seg-{index:05d}.mp4"
            first_row = index * self.rows_per_segment
            last_row = min(first_row + self.rows_per_segment,
                           len(self.table)) - 1
            if last_row < first_row:
                source.unlink(missing_ok=True)
                continue
            filename = f"proxy-{index:05d}.mp4"
            try:
                self.store.release(filename)
                os.replace(source, self.store.directory / filename)
            except OSError:
                continue
            self.store.coverage.record(Span(
                form_key=self.form_key,
                start_pts=self.table.pts_of(first_row),
                end_pts=self.table.pts_of(last_row),
                rows=last_row - first_row + 1,
                filename=filename))
            moved += 1
        self.published += moved
        return moved
