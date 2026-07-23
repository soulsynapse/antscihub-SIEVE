from __future__ import annotations

import threading

from PyQt6.QtCore import QThread, pyqtSignal

from antscihub_sieve.application.intensity import (
    IntensityRequest,
    IntensityResult,
    compute_intensity,
)
from antscihub_sieve.errors import SieveError


class IntensityWorker(QThread):
    progress_changed = pyqtSignal(int, int, int)

    def __init__(self, token: int, request: IntensityRequest) -> None:
        super().__init__()
        self.token = token
        self.request = request
        self.result_value: IntensityResult | None = None
        self.error_value: SieveError | None = None
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    def run(self) -> None:
        try:
            self.result_value = compute_intensity(
                self.request,
                cancelled=self._cancelled.is_set,
                progress=lambda done, total: self.progress_changed.emit(
                    self.token, done, total
                ),
            )
        except SieveError as exc:
            self.error_value = exc
        except BaseException as exc:
            self.error_value = SieveError(
                "INTENSITY_WORKER_FAILED",
                "Intensity worker failed",
                exception_type=type(exc).__name__,
                detail=str(exc),
            )
