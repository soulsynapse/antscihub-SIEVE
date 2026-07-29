






















from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot

from sieve.core.pipeline_model import ClipRange, CropArtifact
from sieve.core.replicates import Replicate
from sieve.pipeline.materialize import MaterializeCancelledError, materialize_crop


@dataclass(frozen=True, slots=True)
class MaterializeRequest:








    video: Path
    replicate: Replicate
    span: ClipRange
    project_dir: Path



    luma: bool


class _Worker(QObject):


    written = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    progressed = Signal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self._cancel = False

    def request_cancel(self) -> None:







        self._cancel = True

    @Slot(MaterializeRequest)
    def write(self, request: MaterializeRequest) -> None:








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














    written = Signal(object)

    failed = Signal(str)

    cancelled = Signal()

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

        return self._busy

    def start(self, request: MaterializeRequest) -> bool:

        if self._busy:
            return False
        self._busy = True
        self._requested.emit(request)
        return True

    def cancel(self) -> None:

        if self._busy:
            self._worker.request_cancel()

    def shutdown(self) -> None:







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
