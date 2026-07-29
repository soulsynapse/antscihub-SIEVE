from __future__ import annotations

from pathlib import Path
from typing import Final

from PySide6.QtCore import QObject, QSettings, Signal


ADAPTIVE_SCRUB: Final = "scrub/adaptive"
DEFAULT_ADAPTIVE_SCRUB: Final = True


COARSE_INTERVAL_SECONDS: Final = "scrub/coarse_interval_seconds"
DEFAULT_COARSE_INTERVAL_SECONDS: Final = 1.0
MIN_COARSE_INTERVAL_SECONDS: Final = 0.25
MAX_COARSE_INTERVAL_SECONDS: Final = 10.0


PROXY_WIDTH: Final = "decode/proxy_width"
DEFAULT_PROXY_WIDTH: Final = 1280
MIN_PROXY_WIDTH: Final = 320
MAX_PROXY_WIDTH: Final = 3840


VIEWPORT_LUMA: Final = "decode/viewport_luma"
DEFAULT_VIEWPORT_LUMA: Final = False


RENDER_FED_PLAYBACK: Final = "playback/render_fed"
DEFAULT_RENDER_FED_PLAYBACK: Final = True


LAST_VIDEO: Final = "session/last_video"


class Preferences(QObject):
    changed = Signal()

    def __init__(
        self, settings: QSettings | None = None, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._settings = settings if settings is not None else QSettings()

    @property
    def adaptive_scrub(self) -> bool:
        return _as_bool(self._settings.value(ADAPTIVE_SCRUB), DEFAULT_ADAPTIVE_SCRUB)

    @adaptive_scrub.setter
    def adaptive_scrub(self, enabled: bool) -> None:
        self._store(ADAPTIVE_SCRUB, bool(enabled), current=self.adaptive_scrub)

    @property
    def coarse_interval_seconds(self) -> float:
        return _as_float(
            self._settings.value(COARSE_INTERVAL_SECONDS),
            DEFAULT_COARSE_INTERVAL_SECONDS,
            MIN_COARSE_INTERVAL_SECONDS,
            MAX_COARSE_INTERVAL_SECONDS,
        )

    @coarse_interval_seconds.setter
    def coarse_interval_seconds(self, seconds: float) -> None:
        self._store(
            COARSE_INTERVAL_SECONDS,
            _clamp(
                float(seconds), MIN_COARSE_INTERVAL_SECONDS, MAX_COARSE_INTERVAL_SECONDS
            ),
            current=self.coarse_interval_seconds,
        )

    @property
    def proxy_width(self) -> int:
        return round(
            _as_float(
                self._settings.value(PROXY_WIDTH),
                float(DEFAULT_PROXY_WIDTH),
                float(MIN_PROXY_WIDTH),
                float(MAX_PROXY_WIDTH),
            )
        )

    @proxy_width.setter
    def proxy_width(self, width: int) -> None:
        self._store(
            PROXY_WIDTH,
            int(_clamp(float(width), MIN_PROXY_WIDTH, MAX_PROXY_WIDTH)),
            current=self.proxy_width,
        )

    @property
    def viewport_luma(self) -> bool:
        return _as_bool(self._settings.value(VIEWPORT_LUMA), DEFAULT_VIEWPORT_LUMA)

    @viewport_luma.setter
    def viewport_luma(self, enabled: bool) -> None:
        self._store(VIEWPORT_LUMA, bool(enabled), current=self.viewport_luma)

    @property
    def render_fed_playback(self) -> bool:
        return _as_bool(
            self._settings.value(RENDER_FED_PLAYBACK), DEFAULT_RENDER_FED_PLAYBACK
        )

    @render_fed_playback.setter
    def render_fed_playback(self, enabled: bool) -> None:
        self._store(
            RENDER_FED_PLAYBACK, bool(enabled), current=self.render_fed_playback
        )

    @property
    def last_video(self) -> Path | None:
        raw = self._settings.value(LAST_VIDEO)
        if not isinstance(raw, str) or not raw.strip():
            return None
        return Path(raw)

    @last_video.setter
    def last_video(self, path: Path | None) -> None:
        stored = self.last_video
        self._store(
            LAST_VIDEO,
            "" if path is None else str(path),
            current="" if stored is None else str(stored),
            notify=False,
        )

    def restore_defaults(self) -> None:
        for key in (
            ADAPTIVE_SCRUB,
            COARSE_INTERVAL_SECONDS,
            PROXY_WIDTH,
            VIEWPORT_LUMA,
            RENDER_FED_PLAYBACK,
        ):
            self._settings.remove(key)
        self._settings.sync()
        self.changed.emit()

    def _store(
        self, key: str, value: object, *, current: object, notify: bool = True
    ) -> None:
        if current == value:
            return
        self._settings.setValue(key, value)
        self._settings.sync()
        if notify:
            self.changed.emit()


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def _as_bool(raw: object, default: bool) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        lowered = raw.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return default


def _as_float(raw: object, default: float, low: float, high: float) -> float:
    if isinstance(raw, bool) or raw is None:
        return default
    if isinstance(raw, int | float):
        return _clamp(float(raw), low, high)
    if isinstance(raw, str):
        try:
            return _clamp(float(raw.strip()), low, high)
        except ValueError:
            return default
    return default
