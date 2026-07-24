from __future__ import annotations

import inspect
import threading
import time
from dataclasses import dataclass
from typing import TypeAlias

from PyQt6.QtCore import QThread, pyqtSignal

from antscihub_sieve.application.channel_progress import ChannelFrame
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


@dataclass(frozen=True, slots=True)
class ScientificPreview:
    frames: tuple[ChannelFrame, ...]

    @property
    def start_frame(self) -> int:
        return self.frames[0].absolute_frame


class ScientificWorker(QThread):
    progress_changed = pyqtSignal(int, int, int)
    preview_ready = pyqtSignal(int, object)

    def __init__(self, token: int, request: ScientificRequest) -> None:
        super().__init__()
        self.token = token
        self.request = request
        self.result_value: ScientificResult | None = None
        self.error_value: SieveError | None = None
        self._cancelled = threading.Event()
        self._preview_frames: list[ChannelFrame] = []
        self._last_preview_emit = time.monotonic()
        self._preview_emitted = False

    def cancel(self) -> None:
        self._cancelled.set()

    def _frame_completed(self, frame: ChannelFrame) -> None:
        self._preview_frames.append(frame)
        now = time.monotonic()
        if (
            (not self._preview_emitted and len(self._preview_frames) >= 8)
            or (
                self._preview_emitted
                and now - self._last_preview_emit >= 0.1
            )
        ):
            self._flush_preview()

    def _flush_preview(self) -> None:
        frames, self._preview_frames = self._preview_frames, []
        if not frames:
            return
        self.preview_ready.emit(
            self.token,
            ScientificPreview(frames=tuple(frames)),
        )
        self._preview_emitted = True
        self._last_preview_emit = time.monotonic()

    def run(self) -> None:
        try:
            compute = (
                compute_change_energy
                if isinstance(self.request, ChangeEnergyRequest)
                else compute_intensity
            )
            arguments = {
                "cancelled": self._cancelled.is_set,
                "progress": lambda done, total: self.progress_changed.emit(
                    self.token, done, total
                ),
            }
            parameters = inspect.signature(compute).parameters.values()
            if any(
                parameter.name == "frame_completed"
                or parameter.kind is inspect.Parameter.VAR_KEYWORD
                for parameter in parameters
            ):
                arguments["frame_completed"] = self._frame_completed
            self.result_value = compute(self.request, **arguments)
        except SieveError as exc:
            self.error_value = exc
        except BaseException as exc:
            self.error_value = SieveError(
                "SCIENTIFIC_WORKER_FAILED",
                "Selected-channel worker failed",
                exception_type=type(exc).__name__,
                detail=str(exc),
            )
        finally:
            self._flush_preview()


# Compatibility import for callers that named the milestone-5 worker. There is
# one implementation and one live scientific owner.
IntensityWorker = ScientificWorker
