"""The write pass on its own thread: one crop, cut while the GUI stays alive.

`pipeline/materialize.py` is a minute of sequential decode with a read-back on
the end of it, and it is a plain function on purpose — the CLI calls it and
blocks. The GUI cannot: an event loop stopped for 46 seconds is an application
that has hung, and the two things this pass owes the user while it runs are
exactly the two a stopped loop cannot give — where it has got to, and a way to
stop it.

**Cancellation is real here, unlike the detector's.** `materialize_crop` polls a
callable once per fed frame, so a flag has thousands of boundaries to be read
at rather than one, and the writer already deletes the part file on the way out
(`MaterializeCancelledError`). The flag is a plain `bool` written from the GUI
thread and read from the worker: one writer, one reader, one direction, and a
torn read of a boolean is not a thing CPython admits.

**Nothing here decides anything.** The worker is handed the video, the
replicate, the span, and the format, and reports what came back. Which format
is `not graph_needs_chroma`, which span is the document's window, and whether
the preview is paused around it are all the tab's, because they are all
questions about the session rather than about the write.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot

from sieve.core.pipeline_model import ClipRange, CropArtifact
from sieve.core.replicates import Replicate
from sieve.pipeline.materialize import MaterializeCancelledError, materialize_crop


@dataclass(frozen=True, slots=True)
class MaterializeRequest:
    """One cut to write. Crosses to the worker whole.

    Frozen and carried entire for `ResolvedSource`'s reason one layer up: the
    format and the span are not independent choices a caller may recombine —
    they are what the record will claim, and a request assembled field by field
    on the far side could claim a span it did not write.
    """

    video: Path
    replicate: Replicate
    span: ClipRange
    project_dir: Path
    #: `not graph_needs_chroma(pipeline)` for the graph that will read the file.
    #: Derived by the caller, never chosen: a colour artifact in a luma session
    #: is the wrong-pixels trap the codec finding measured.
    luma: bool


class _Worker(QObject):
    """Lives on the write thread. Its one slot runs off the GUI thread."""

    written = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    progressed = Signal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self._cancel = False

    def request_cancel(self) -> None:
        """Withdraw the running write. Called from the GUI thread, deliberately.

        Not a slot and not queued: a queued cancellation would sit behind the
        write in this thread's event queue and be delivered when the write was
        already over, which is a cancel button that does nothing for a minute
        and then nothing at all.
        """
        self._cancel = True

    @Slot(MaterializeRequest)
    def write(self, request: MaterializeRequest) -> None:
        """Cut, verify, and report. One of the three signals always goes out.

        Every failure is reported rather than raised, and reported as a
        sentence: this is a file the user asked for over footage they chose, so
        a missing parent, a codec that refused, and a file that did not read
        back as what was fed are all ordinary outcomes of a gesture and all of
        them belong on screen. The writer has already deleted whatever it left.
        """
        self._cancel = False
        try:
            record = materialize_crop(
                request.video,
                request.replicate,
                request.span,
                project_dir=request.project_dir,
                luma=request.luma,
                cancelled=lambda: self._cancel,
                progress=self.progressed.emit,
            )
        except MaterializeCancelledError:
            self.cancelled.emit()
            return
        except (OSError, RuntimeError, ValueError) as error:
            self.failed.emit(str(error))
            return
        self.written.emit(record)


class MaterializeRunner(QObject):
    """Writes crop artifacts off the GUI thread, one at a time.

    Construct on the GUI thread. Owns its thread for its whole life, so
    `shutdown` is required before the application exits — the same obligation
    `PreviewRunner`, `VideoPlayer`, and `DetectorRunner` carry.

    One write at a time and no queue: a second request while one is running is
    refused rather than pended. Two concurrent write passes are two sequential
    decodes of the same file competing for the bandwidth the pause exists to
    hand to one of them, and "materialize all of them" is a batch gesture the
    CLI already spells as a shell loop.
    """

    #: A verified artifact was written, as a `CropArtifact` to register.
    written = Signal(object)
    #: The write could not be completed, with the reason as the user can read it.
    failed = Signal(str)
    #: The user withdrew. No file was left behind.
    cancelled = Signal()
    #: `(frames written, frames total)` — once per fed frame.
    progressed = Signal(int, int)

    _requested = Signal(MaterializeRequest)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._busy = False

        self._thread = QThread()
        self._thread.setObjectName("sieve-materialize")
        self._worker = _Worker()
        self._worker.moveToThread(self._thread)
        self._requested.connect(self._worker.write)
        self._worker.written.connect(self._on_written)
        self._worker.failed.connect(self._on_failed)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.progressed.connect(self.progressed)
        self._thread.start()

    @property
    def busy(self) -> bool:
        """Whether a write is running."""
        return self._busy

    def start(self, request: MaterializeRequest) -> bool:
        """Begin `request`. Returns whether it was accepted."""
        if self._busy:
            return False
        self._busy = True
        self._requested.emit(request)
        return True

    def cancel(self) -> None:
        """Withdraw the running write, if there is one."""
        if self._busy:
            self._worker.request_cancel()

    def shutdown(self) -> None:
        """Stop the write thread, withdrawing anything running.

        The cancel comes first and the wait is unbounded on purpose: the flag is
        read once per frame, so the pass returns within one decode, and quitting
        the thread under a write would abandon a part file on disk — which is
        the one thing the writer's atomicity is built to make impossible.
        """
        self.cancel()
        self._thread.quit()
        self._thread.wait()

    @Slot(object)
    def _on_written(self, record: CropArtifact) -> None:
        self._busy = False
        self.written.emit(record)

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        self._busy = False
        self.failed.emit(message)

    @Slot()
    def _on_cancelled(self) -> None:
        self._busy = False
        self.cancelled.emit()
