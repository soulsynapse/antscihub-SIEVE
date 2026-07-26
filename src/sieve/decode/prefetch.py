"""N readers over one file, reading ahead in order, so the convert is not the rate.

`VideoReader.read` on the reference source is 24.5 ms, of which 1.2 ms is decode
and the rest is a full-frame YUV420→BGR24 conversion performed single-threaded on
the calling thread. ffmpeg does the identical work at 2.95 ms per frame by
spreading that conversion across the machine. OpenCV exposes no way to reach the
conversion separately, so what this parallelises is whole `read` calls: N readers,
one per thread, reading ahead of one consumer.

**It gets 1.61x, not the 9x that gap suggests, and the shape of the curve is the
interesting part.** Throughput peaks at four workers (15.25 ms/frame) and then
*degrades* — 20.45 at eight, 28.49 at twelve, which is worse than a single thread
on a machine with thirty-two cores. Cores are not the limit. Each `read`
allocates a fresh 47.6 MB BGR array and frees it, so four workers already move
about 3 GB/s of writes plus the YUV reads, and adding workers adds concurrent
large allocations whose page faults serialise in the kernel. ffmpeg does not hit
this wall because its `AVFrame` pool recycles buffers rather than returning them
to the allocator every frame.

The consequence worth carrying: the remaining 6x is in *not materialising a
full-resolution BGR frame per frame* — cropping before the convert, or taking the
luma plane alone — and none of that is reachable from here. Numbers and the four
routes are in
`docs/findings/2026.07.26-threading-the-reads-buys-1.6x-and-stops.md`.

**Every frame is byte-identical to what `VideoReader` returns, and that is the
constraint the design is shaped around.** `cache_key.source_key` folds
`decoder_identity()` into the ancestor of every node, so a reader that changed a
pixel would silently invalidate — or worse, silently *not* invalidate — every
entry in every store. There is no new decode path here: each worker owns an
ordinary `VideoReader` and calls `read(index)` on it. Nothing crops, nothing
converts, nothing resamples. That is why this needs no decoder identity of its
own and why it can be turned on without a cache generation, which the three
faster routes in that finding cannot.

**Interleaved, not chunked, because the consumer wants frames in order.**
Splitting a span into N contiguous blocks is the obvious decomposition and it is
wrong here: the consumer reads frame 0, then 1, then 2, so block N-1's worker
would have to hold its whole block until the consumer arrived, and the peak
memory would be the span rather than a window. Instead the workers claim from a
sliding window of `lookahead` indices just ahead of what the consumer wants, so
at any moment they are decoding adjacent frames and at most `lookahead` frames
exist. Each worker's next claim is typically `workers` frames ahead of its last,
and `VideoReader._position_at` already grabs through a gap that small rather than
seeking — a 1.2 ms grab per skipped frame against a ~50 ms seek — so the
decomposition costs grabs and never seeks.

**A jump abandons the window.** `read` at anything other than the next expected
index bumps an epoch counter, discards what was claimed for the old position, and
starts over. Work already in flight cannot be recalled, so it is stamped and
dropped on arrival — borrowed from `gui/coalescer.py`'s `generation`, though *not*
for the same reason, and the difference is worth stating because the resemblance
invites the wrong one.

The coalescer's stamp is a correctness mechanism: a frame decoded against a closed
video would be painted into the next one. Here it is only hygiene. A frame for
index `i` is the same frame whichever epoch asked for it — same reader, same
index, same bytes — so serving a stale one could not produce a wrong answer, and
deleting the epoch comparison entirely passes every test in
`tests/integration/test_prefetch_decode.py`. What it actually buys is that up to
`workers` frames from an abandoned position do not linger in the completed map,
and that a decode failure recorded for one position is not raised at a caller who
has since moved somewhere else. Both are bounded and neither is a wrong frame.

The real cost of a jump is the wasted reads, and that is why this is opt-in rather
than what `VideoReader` became: a scrubbing GUI jumps constantly and would pay up
to `workers` abandoned reads on every drag, while `pipeline/executor.py` walks
`decode_range` strictly forward and pays it once.

**The worker count is machine capability and never project state.** It reaches a
run as an invocation option, exactly as VISION step 6 splits it — the artifact
describes what is computed, and a `threads:` field in it would make one machine's
allocation part of another machine's reproducible document. `resolve_workers` is
the one place that decides a count when the caller did not, and that plus a
`--workers` flag is the whole of what this owes a cluster: no scheduler-specific
environment variables, for the reasons in that function's docstring.
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import Condition, Thread
from types import TracebackType
from typing import Self

from sieve.core.types import Frame, VideoMetadata
from sieve.decode.reader import VideoDecodeError, VideoReader

#: Ceiling on an *inferred* worker count, and a measured number rather than a
#: guess about memory: on the reference source, throughput peaks at four workers
#: (15.25 ms/frame against a sequential 24.50) and *degrades* past six, reaching
#: 28.49 ms — worse than one thread — at twelve, on a machine with thirty-two
#: cores. The limit is not cores; see the module docstring.
#:
#: So this cap is where the curve turns, which makes guessing high actively
#: harmful rather than merely wasteful. An explicit request is still never
#: capped: the curve belongs to this footage on this machine, and a cluster node
#: measuring its own is the caller that should win.
INFERRED_WORKER_CAP = 4


def available_cpus() -> int:
    """CPUs this process may actually use, not the ones the machine has.

    `os.cpu_count()` reports the machine and is the wrong answer inside a cgroup,
    a container, or a job step pinned to a subset of a node — all three being the
    ordinary case on the hardware this is meant to run on. `sched_getaffinity` is
    the right answer and exists only on Linux, which is why the fallback is here
    rather than at the call site.
    """
    affinity = getattr(os, "sched_getaffinity", None)
    if affinity is not None:
        return max(len(affinity(0)), 1)
    return max(os.cpu_count() or 1, 1)


def resolve_workers(requested: int | None = None) -> int:
    """How many decode threads to run: the request, else what the machine allows.

    **The one definition, so that a second caller cannot invent a different
    answer.** `workers/manager.py` will want the same number for process pools
    and should call this rather than re-deriving it — a run whose decode threads
    and compute processes disagreed about how much of a node they had would
    oversubscribe it, and the symptom is a slow job rather than a failure.

    A request always wins and is never capped: `INFERRED_WORKER_CAP` bounds a
    guess about a machine this code cannot see, and a cluster node passing 32 can
    see it.

    **Deliberately does not read the environment.** An earlier version consulted
    `SLURM_CPUS_PER_TASK` and a `SIEVE_DECODE_WORKERS` override, and both were
    dropped: `available_cpus` already returns a job step's allocation under the
    usual affinity and cgroup plugins, a SLURM-only variable reads as scheduler
    coverage while doing nothing for PBS, LSF, or SGE, and an override is a
    second way to say what `--workers` says. A batch script passing
    `--workers $SLURM_CPUS_PER_TASK` puts the number where a person debugging a
    slow job will look for it, which is also what VISION step 6 asks for —
    machine capability reaches a run as a command-line option.

    Returns:
        A count of at least 1. One worker is the sequential path — a single
        reader on a single thread — so a caller never has to branch on it.
    """
    if requested is not None:
        return max(requested, 1)
    return min(available_cpus(), INFERRED_WORKER_CAP)


class PrefetchFrameSource:
    """A `FrameSource` that decodes ahead of the caller on `workers` threads.

    Satisfies the protocol `pipeline/executor.py` takes, so it is passed to
    `execute` in place of a `VideoReader` and nothing above changes. Frames are
    byte-identical either way; the difference is only how many are being decoded
    at once.

    Safe for one consumer thread. Not a shared cache: two threads calling `read`
    with different indices would fight over the window and each would see the
    other's jumps as its own.
    """

    def __init__(
        self,
        path: Path | str,
        *,
        workers: int | None = None,
        lookahead: int | None = None,
    ) -> None:
        """Open `path` `workers` times and start reading ahead of the caller.

        Args:
            path: The video. Opened once per worker, because a `VideoCapture`
                carries the decoder position and two threads sharing one would
                interleave their seeks.
            workers: Decode threads. `None` asks `resolve_workers`.
            lookahead: How far ahead of the consumer indices may be claimed, and
                therefore the ceiling on frames held at once. Defaults to twice
                the worker count — the value every number in the module docstring
                was measured at. With a window exactly as wide as the pool, a
                worker that finishes out of order has nothing left to claim and
                idles until the consumer catches up. Peak memory is this many
                full-resolution frames — 47.6 MB each on the reference source —
                and that arithmetic, not the core count, is what bounds a
                sensible worker count on a laptop.

        Raises:
            VideoDecodeError: if the file cannot be opened or reports no frames.
                Raised from the first reader, before any thread starts, so a bad
                path fails the same way it does for `VideoReader`.
        """
        self._path = Path(path)
        self._worker_count = resolve_workers(workers)
        self._lookahead = self._worker_count * 2 if lookahead is None else max(lookahead, 1)

        self._readers = self._open_readers()
        self._metadata = self._readers[0].metadata

        # One lock for the window, the results, and the epoch. A finer split
        # would be three locks a worker takes in sequence to publish one frame.
        self._state = Condition()
        self._started = False
        self._want = 0
        self._claim = 0
        self._epoch = 0
        self._done: dict[int, Frame] = {}
        self._failed: dict[int, VideoDecodeError] = {}
        self._closed = False

        self._threads = [
            Thread(target=self._serve, args=(reader,), name=f"sieve-decode-{number}", daemon=True)
            for number, reader in enumerate(self._readers)
        ]
        for thread in self._threads:
            thread.start()

    def _open_readers(self) -> list[VideoReader]:
        """One `VideoReader` per worker, or none at all.

        Closes what it opened if a later one fails, because a half-opened source
        would hold capture handles that nothing has a reference to — and the
        caller is about to see an exception rather than an object it can `close`.
        """
        readers: list[VideoReader] = []
        try:
            for _ in range(self._worker_count):
                readers.append(VideoReader(self._path))
        except VideoDecodeError:
            for reader in readers:
                reader.close()
            raise
        return readers

    # ---- state -----------------------------------------------------------

    @property
    def metadata(self) -> VideoMetadata:
        """Container-reported properties of the open file."""
        return self._metadata

    @property
    def workers(self) -> int:
        """How many decode threads are running."""
        return self._worker_count

    @property
    def lookahead(self) -> int:
        """Ceiling on frames claimed but not yet consumed."""
        return self._lookahead

    # ---- reading ---------------------------------------------------------

    def read(self, index: int) -> Frame:
        """The frame at `index`, waiting for it if a worker is still on it.

        Sequential calls are the fast path and the only one worth having this
        class for: `index` is already claimed, probably already decoded, and the
        window slides forward as it is consumed. Any other `index` restarts the
        window there and discards what was in flight.

        Raises:
            VideoDecodeError: if `index` is outside the video, if the frame
                cannot be decoded, or if the source has been closed. The
                out-of-range message matches `VideoReader`'s, because a caller
                should not be able to tell which source refused it.
        """
        if not 0 <= index < self._metadata.frame_count:
            raise VideoDecodeError(
                f"Frame {index} out of range 0..{self._metadata.frame_count - 1}"
            )

        with self._state:
            if not self._started or index != self._want:
                self._restart(index)
            while True:
                if self._closed:
                    raise VideoDecodeError(f"Reader for {self._path} is closed")
                frame = self._done.pop(index, None)
                if frame is not None:
                    self._want = index + 1
                    self._state.notify_all()
                    return frame
                failure = self._failed.pop(index, None)
                if failure is not None:
                    # Point the window back at the frame that failed rather than
                    # past it. A caller that retries gets a fresh attempt on a
                    # reader that has already been forced to re-seek, and one
                    # that gives up — which is every caller today — loses
                    # nothing by the window being where it is.
                    self._restart(index)
                    raise failure
                self._state.wait()

    def _restart(self, index: int) -> None:
        """Aim the window at `index`, abandoning everything claimed before it.

        The epoch bump lets workers mid-read finish into nothing rather than being
        interrupted. It is hygiene rather than correctness — see the module
        docstring, which says why a stale frame could not be a wrong one — so what
        it prevents is a stale entry lingering and a stale failure resurfacing, not
        a bad answer. Caller holds `self._state`.
        """
        self._started = True
        self._epoch += 1
        self._want = index
        self._claim = index
        self._done.clear()
        self._failed.clear()
        self._state.notify_all()

    def _serve(self, reader: VideoReader) -> None:
        """One worker: claim the next index in the window, decode it, publish it.

        The read happens outside the lock, which is the entire point — N workers
        converting concurrently is what buys the speedup, and a worker holding
        the lock across its `read` would serialise them back into one.
        """
        while True:
            with self._state:
                while not self._closed and not self._claimable():
                    self._state.wait()
                if self._closed:
                    return
                epoch = self._epoch
                index = self._claim
                self._claim += 1

            try:
                frame = reader.read(index)
            except VideoDecodeError as error:
                self._publish(epoch, index, error=error)
                continue
            self._publish(epoch, index, frame=frame)

    def _claimable(self) -> bool:
        """Whether an index is available to claim. Caller holds `self._state`."""
        return (
            self._started
            and self._claim < self._want + self._lookahead
            and self._claim < self._metadata.frame_count
        )

    def _publish(
        self,
        epoch: int,
        index: int,
        *,
        frame: Frame | None = None,
        error: VideoDecodeError | None = None,
    ) -> None:
        """Hand a result to the consumer, unless the window has moved since.

        Notifies even when the result is dropped: the consumer may be waiting on
        an index this worker is no longer going to produce, and the other workers
        may be waiting on a window this one's claim is holding open.
        """
        with self._state:
            if epoch == self._epoch:
                if frame is not None:
                    self._done[index] = frame
                if error is not None:
                    self._failed[index] = error
            self._state.notify_all()

    # ---- lifecycle -------------------------------------------------------

    def close(self) -> None:
        """Stop the workers and release every capture. Idempotent.

        Joins before closing the readers, because a worker mid-`read` holds one —
        so this blocks for at most one frame's decode per worker, which is the
        price of not releasing a capture underneath the thread using it.
        """
        with self._state:
            if self._closed:
                return
            self._closed = True
            self._state.notify_all()
        for thread in self._threads:
            thread.join()
        for reader in self._readers:
            reader.close()
        with self._state:
            self._done.clear()
            self._failed.clear()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
