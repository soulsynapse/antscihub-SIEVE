from __future__ import annotations

import threading
from typing import TypeAlias

from PyQt6.QtCore import QThread, pyqtSignal

from antscihub_sieve.application.change_energy import (
    ChangeEnergyRequest,
    ChangeEnergyResult,
    compute_change_energy,
)
from antscihub_sieve.application.intensity import (
    IntensityRequest,
    IntensityResult,
    compute_intensity,
)
from antscihub_sieve.errors import SieveError


ScientificRequest: TypeAlias = IntensityRequest | ChangeEnergyRequest
ScientificResult: TypeAlias = IntensityResult | ChangeEnergyResult


class ScientificWorker(QThread):
    progress_changed = pyqtSignal(int, int, int)

    def __init__(self, token: int, request: ScientificRequest) -> None:
        super().__init__()
        self.token = token
        self.request = request
        self.result_value: ScientificResult | None = None
        self.error_value: SieveError | None = None
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    def run(self) -> None:
        try:
            compute = (
                compute_change_energy
                if isinstance(self.request, ChangeEnergyRequest)
                else compute_intensity
            )
            self.result_value = compute(
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
                "SCIENTIFIC_WORKER_FAILED",
                "Selected-channel worker failed",
                exception_type=type(exc).__name__,
                detail=str(exc),
            )


# Compatibility import for callers that named the milestone-5 worker. There is
# one implementation and one live scientific owner.
IntensityWorker = ScientificWorker
