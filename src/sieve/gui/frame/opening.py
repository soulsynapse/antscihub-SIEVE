"""Opening a recording without stopping the window.

The first genuinely slow thing SIEVE does, and the one place the freeze finding's
rule would be easiest to break by accident. Opening a recording builds its frame
table — a demux of every packet, seconds on the footage this tree runs on
(`docs/findings/2026.08.21-keyframe-index-is-cheap-and-the-gop-is-fixed.md`) —
and, the first time on a given machine and source shape, races the decoders to
decide which one seeks faster. Neither belongs on the thread that draws.

**So the session is built on a worker and handed back through a signal.** The
window stays live throughout: the library still scrolls, the swipe still slides,
and the canvas says what it is waiting for rather than going grey. What arrives
is a `Session`, already open, which the window then uses on its own thread the
way everything else does.

**A second open supersedes the first.** Somebody clicks one recording, changes
their mind and clicks another before the first has finished; the first session
is closed as it lands rather than being left holding a decoder and a frame table
nobody will look at. That is what `generation` is for — the alternative is
cancellation plumbing through a table build that has no safe place to stop.

**Failures arrive the same way successes do.** A recording that has been unplugged
between the library drawing it and somebody clicking it is the ordinary case, not
an exception: it comes back as a message rather than a traceback, because the
window has to say something and a dialog raised from a worker is not a thing Qt
will let it say.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal

from sieve.project.project import Project
from sieve.session.session import Session


class Opener(QObject):
    """Builds sessions off the drawing thread, one at a time.

    A `QObject` rather than a bare thread because what has to cross back is a
    Python object arriving on the GUI thread, and a signal is the one way Qt
    will do that safely. The worker itself is an ordinary thread: there is
    nothing for an event loop to do inside a demux.
    """

    #: A session is open and belongs to the window now. Carries the project it
    #: is of, because by the time it lands the library's selection may have
    #: moved and the window has to know what it was handed.
    opened = Signal(object, object)      # Project, Session

    #: Something went wrong, in words a person can be shown.
    failed = Signal(object, str)         # Project, reason

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._generation = 0
        self._lock = threading.Lock()

    def open(self, project: Project, **kwargs) -> None:
        """Start building a session for `project`. Returns immediately."""
        with self._lock:
            self._generation += 1
            mine = self._generation

        def work() -> None:
            try:
                session = project.session(**kwargs)
            except Exception as reason:  # noqa: BLE001 - shown, not raised
                if self._current(mine):
                    self.failed.emit(project, str(reason))
                return
            if not self._current(mine):
                # somebody asked for a different recording while this one was
                # opening. Closed here rather than handed over: a session that
                # nobody will look at still holds a decoder open.
                session.close()
                return
            self.opened.emit(project, session)

        threading.Thread(target=work, daemon=True,
                         name=f"open-{project.name}").start()

    def _current(self, generation: int) -> bool:
        with self._lock:
            return generation == self._generation
