"""Running a step off the thread that draws, one in flight and one pending.

The arithmetic does not fit the frame period and cannot be made to: measured on
the 5.3K footage, the field is the bulk of it and `goodFeaturesToTrack` costs
the same whether it keeps five hundred corners or a hundred and fifty, because
what it pays for is the response map over the whole image. So the loop cannot
be made to keep up frame for frame, and the fix is not to try.

Ported in shape from v2's `gui/preview_runner.py`, whose rule applies here
unchanged: there is one desired overlay at any moment and it is always for the
most recent position, so a result for a position the user has already left is
work nobody would have seen. One render in flight, one pending, later
overwrites the pending one.

**A revision number rather than a cancel flag.** A flag has to be raised by one
thread and lowered by the other, and there is no safe moment for the lowering —
the drawing thread cannot lower it when it issues the next request, because the
worker may not yet have reached the point where it would have seen it raised.
A number each side only ever *compares* has no such moment. `_Wanted` is a
guarded integer and not a bare attribute for the reason v2 gives: assignment to
an `int` is atomic in CPython today, and a shared mutable that is correct by
accident of the interpreter is still there when the accident stops holding.

**The tiers are read on the thread that owns them.** `Session.step_inputs` runs
here, on the GUI thread, and only the arithmetic and the paint cross over — so
the fill, the chunks and the proxy keep one caller and this buys no concurrency
it would have to defend.

**That read waits for the issue, not the request.** It is cheap when the
neighbourhood is resident and a cold chunk fetch when it is not, and a request
that goes straight into the pending slot is about to be overwritten — fetching
for it would pay the expensive case to throw the frames away. Deferring it
means a burst costs one read per issue rather than one per request.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, Slot

from sieve import surfaces


class _Wanted:
    """The newest revision: written by the drawing thread, read by the worker."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._revision = 0

    def set(self, revision: int) -> None:
        """Declare *revision* the only one still worth computing."""
        with self._lock:
            self._revision = revision

    def is_current(self, revision: int) -> bool:
        with self._lock:
            return revision == self._revision


class _Worker(QObject):
    """The field and the paint, on a thread of its own."""

    done = Signal(int, object, float, float)   # revision, image, value, ceiling

    def __init__(self, wanted: _Wanted) -> None:
        super().__init__()
        self._wanted = wanted

    @Slot(object)
    def run(self, job: tuple) -> None:
        revision, step, frames, ordinal, display, ceiling = job
        # Asked before the expensive part and again before the paint: a
        # request superseded while it sat in the queue should cost nothing.
        if not self._wanted.is_current(revision):
            self.done.emit(revision, None, 0.0, ceiling)
            return
        field, value = _run(step, frames, ordinal)
        if not ceiling:
            # The first honest field sets the top; the session holds it from
            # here, so a still scene is not drawn as hot as a moving one.
            ceiling = max(float(field.max()), 1.0)
        if not self._wanted.is_current(revision):
            self.done.emit(revision, None, 0.0, ceiling)
            return
        self.done.emit(revision, surfaces.overlay(display, field, ceiling),
                       value, ceiling)


def _run(step: Any, frames: Any, ordinal: int) -> tuple:
    """Indirection kept so the worker imports no session module."""
    field = step.field(frames, ordinal)
    return field, float(step.reduce(field))


class StepRunner(QObject):
    """Issues overlay work and hands back only what is still wanted.

    `painted` carries a frame with the field already drawn on it, or nothing
    when the request was superseded or the step could not be fed.
    """

    painted = Signal(object, float, float)    # image, value, ceiling
    _wanted_run = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._wanted = _Wanted()
        self._revision = 0
        self._in_flight: int | None = None
        self._pending: tuple | None = None

        self._thread = QThread()
        self._thread.setObjectName("sieve-step")
        self._worker = _Worker(self._wanted)
        self._worker.moveToThread(self._thread)
        self._wanted_run.connect(self._worker.run)
        self._worker.done.connect(self._settle)
        self._thread.start()

    def request(self, session: Any, position: int, display: Any) -> None:
        """Ask for *position*'s overlay over *display*. Returns immediately.

        Only the revision is claimed here. The tier read waits for `_issue`,
        because a request that goes straight into the pending slot will be
        overwritten by the next one and the frames it fetched thrown away —
        a burst of twenty during a playback run costs two reads, not twenty.
        """
        self._revision += 1
        self._wanted.set(self._revision)
        want = (self._revision, session, position, display)
        if self._in_flight is None:
            self._issue(want)
        else:
            self._pending = want

    def reset(self) -> None:
        """Abandon anything outstanding — the source or the crop has changed."""
        self._revision += 1
        self._wanted.set(self._revision)
        self._pending = None

    def shutdown(self) -> None:
        self.reset()
        self._thread.quit()
        self._thread.wait(2000)

    def _issue(self, want: tuple) -> None:
        """Read the tiers and hand the arithmetic over. On the caller's thread.

        A position whose neighbourhood is not resident yet produces nothing —
        the fill or the proxy will reach it and the next request will find it —
        so the slot is left free and whatever is pending goes instead.
        """
        revision, session, position, display = want
        got = session.step_inputs(position)
        if got is None:
            pending, self._pending = self._pending, None
            if pending is not None:
                self._issue(pending)
            return
        step, frames, ordinal = got
        self._in_flight = revision
        self._wanted_run.emit(
            (revision, step, frames, ordinal, display, session.ceiling)
        )

    @Slot(int, object, float, float)
    def _settle(self, revision: int, image: Any, value: float,
                ceiling: float) -> None:
        """One result is back. Free the slot, issue what waited, draw if wanted."""
        if self._in_flight == revision:
            self._in_flight = None
            pending, self._pending = self._pending, None
            if pending is not None:
                self._issue(pending)
        if image is not None and self._wanted.is_current(revision):
            self.painted.emit(image, value, ceiling)
