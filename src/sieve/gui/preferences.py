"""User preferences: typed accessors over `QSettings`, with change signals.

`QSettings` rather than a file in the project, deliberately. These are machine
preferences — how fast this computer decodes, how much memory to spend on a
proxy — and non-negotiable #2 says GUI-only state stays out of the pipeline
artifact. A preference that travelled with a project would arrive on another
machine as an assertion about hardware it has never seen.

Everything here is consumed by something. A preference nobody reads is a
promise the application does not keep, so the pane stays small on purpose:
each entry below has exactly one call site that changes behaviour.

`QSettings` returns whatever the backing store parsed — strings from an INI
file, real types from the Windows registry — so every read goes through a
coercion that falls back to the default rather than trusting the store.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from PySide6.QtCore import QObject, QSettings, Signal

from sieve.core.clip_window import DEFAULT_WINDOW_SECONDS

#: Switch to coarse seeking when scrubbing cannot keep up. See `scrub_policy`.
ADAPTIVE_SCRUB: Final = "scrub/adaptive"
DEFAULT_ADAPTIVE_SCRUB: Final = True

#: Grid spacing, in seconds of source time, used while coarse mode is active.
COARSE_INTERVAL_SECONDS: Final = "scrub/coarse_interval_seconds"
DEFAULT_COARSE_INTERVAL_SECONDS: Final = 1.0
MIN_COARSE_INTERVAL_SECONDS: Final = 0.25
MAX_COARSE_INTERVAL_SECONDS: Final = 10.0

#: Width frames are decoded down to for display. Wide enough that the viewport
#: is the limit on what can be seen, narrow enough that the resample is cheap.
PROXY_WIDTH: Final = "decode/proxy_width"
DEFAULT_PROXY_WIDTH: Final = 1280
MIN_PROXY_WIDTH: Final = 320
MAX_PROXY_WIDTH: Final = 3840

#: Decode the viewport in grayscale. A speed decision, not a viewing one: the
#: luma path is ~2.4x cheaper per frame and the graphs read luma either way.
#: Written by the viewport's own toggle (`gui/gray_toggle.py`), never by a
#: dialog — the person who needs it is watching a stuttering pane and does not
#: know colour is what they are paying for.
VIEWPORT_LUMA: Final = "decode/viewport_luma"
DEFAULT_VIEWPORT_LUMA: Final = False

#: Serve playback from the render's own frames when it has them, instead of
#: decoding the same file a second time. Beside `ADAPTIVE_SCRUB` in spirit and
#: in the pane: an automatic behaviour the user may not want. Off means the
#: player decodes independently and stutters during renders — the right choice
#: for someone who needs true wall-clock coverage of the whole window more
#: than smooth motion.
RENDER_FED_PLAYBACK: Final = "playback/render_fed"
DEFAULT_RENDER_FED_PLAYBACK: Final = True

#: The last video successfully opened, reoffered at the next launch. Session
#: state rather than a tunable: it has no entry in the preferences pane and is
#: written by the window, not by the user.
LAST_VIDEO: Final = "session/last_video"

#: How long the working window was, the last time the user set its length.
#: Session state for `LAST_VIDEO`'s reason — no pane entry, written by the
#: window rather than chosen in a dialog — and stored in seconds rather than
#: frames because it outlives the video it was set on: the next file may not
#: share its frame rate, and "ten seconds" is what the user meant either way.
#: Read by `core/clip_window.default_window` through the document, so it moves
#: the window a session opens with, never a window a project already names.
WINDOW_SECONDS: Final = "session/window_seconds"
MIN_WINDOW_SECONDS: Final = 0.01
MAX_WINDOW_SECONDS: Final = 24.0 * 60.0 * 60.0


class Preferences(QObject):
    """The application's preferences, persisted immediately on change."""

    #: One signal for the whole store rather than one per key: consumers are
    #: cheap to re-read and there is no ordering hazard in reapplying all of
    #: them, whereas per-key signals would multiply as the pane grows.
    changed = Signal()

    def __init__(self, settings: QSettings | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # An injected store is what lets tests run against a temporary INI file
        # instead of writing to the developer's actual registry.
        self._settings = settings if settings is not None else QSettings()

    # ---- accessors -------------------------------------------------------

    @property
    def adaptive_scrub(self) -> bool:
        """Whether the player may degrade to coarse seeking on its own."""
        return _as_bool(self._settings.value(ADAPTIVE_SCRUB), DEFAULT_ADAPTIVE_SCRUB)

    @adaptive_scrub.setter
    def adaptive_scrub(self, enabled: bool) -> None:
        self._store(ADAPTIVE_SCRUB, bool(enabled), current=self.adaptive_scrub)

    @property
    def coarse_interval_seconds(self) -> float:
        """Coarse-mode grid spacing, in seconds of source time."""
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
            _clamp(float(seconds), MIN_COARSE_INTERVAL_SECONDS, MAX_COARSE_INTERVAL_SECONDS),
            current=self.coarse_interval_seconds,
        )

    @property
    def proxy_width(self) -> int:
        """Display decode width in pixels."""
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
        """Whether the viewport decodes grayscale for speed."""
        return _as_bool(self._settings.value(VIEWPORT_LUMA), DEFAULT_VIEWPORT_LUMA)

    @viewport_luma.setter
    def viewport_luma(self, enabled: bool) -> None:
        self._store(VIEWPORT_LUMA, bool(enabled), current=self.viewport_luma)

    @property
    def render_fed_playback(self) -> bool:
        """Whether the player may take frames from the render instead of decoding."""
        return _as_bool(self._settings.value(RENDER_FED_PLAYBACK), DEFAULT_RENDER_FED_PLAYBACK)

    @render_fed_playback.setter
    def render_fed_playback(self, enabled: bool) -> None:
        self._store(RENDER_FED_PLAYBACK, bool(enabled), current=self.render_fed_playback)

    @property
    def last_video(self) -> Path | None:
        """The video to reoffer at launch, or `None` if there is nothing to offer.

        A path is not validated here. Whether the file still exists is a
        question about the filesystem now, not about what was stored, and the
        caller is the only one that knows what to do when the answer is no.
        """
        raw = self._settings.value(LAST_VIDEO)
        if not isinstance(raw, str) or not raw.strip():
            return None
        return Path(raw)

    @last_video.setter
    def last_video(self, path: Path | None) -> None:
        # Silent: `changed` means "reapply the settings you run on", and this
        # key changes nobody's behaviour until the next launch. Emitting it
        # would make every video that opens look like a preference edit.
        stored = self.last_video
        self._store(
            LAST_VIDEO,
            "" if path is None else str(path),
            current="" if stored is None else str(stored),
            notify=False,
        )

    @property
    def window_seconds(self) -> float:
        """The window length a new session opens with, in seconds."""
        return _as_float(
            self._settings.value(WINDOW_SECONDS),
            DEFAULT_WINDOW_SECONDS,
            MIN_WINDOW_SECONDS,
            MAX_WINDOW_SECONDS,
        )

    @window_seconds.setter
    def window_seconds(self, seconds: float) -> None:
        # Silent, like `last_video`: every window edit passes through here, and
        # `changed` means "reapply the settings you run on" — a decode pipeline
        # rebuilt on each drag of the timeline bracket would be the cost of a
        # key nothing running reads.
        self._store(
            WINDOW_SECONDS,
            _clamp(float(seconds), MIN_WINDOW_SECONDS, MAX_WINDOW_SECONDS),
            current=self.window_seconds,
            notify=False,
        )

    # ---- bulk ------------------------------------------------------------

    def restore_defaults(self) -> None:
        """Drop every tunable, emitting one change rather than one per key.

        The `session/` keys are deliberately not in the list. Restoring defaults
        is a statement about how the application should behave, and forgetting
        which file the user was working on — or how long a stretch of it they
        work in — is not one of the things they asked for.
        """
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

    def _store(self, key: str, value: object, *, current: object, notify: bool = True) -> None:
        """Write `value` under `key`, emitting `changed` only if it is new.

        `current` is the caller's *typed* reading of the preference, not the
        raw stored value. Comparing raw against typed is the exact mismatch
        `_as_bool`/`_as_float` exist to absorb, and it hides in testing: within
        one process `QSettings` answers from its own cache and hands back the
        `int` it was given, so the guard holds. It is the *next launch* that
        parses the INI off disk and hands back `"1920"`, which equals nothing,
        and every reopened preference then rewrites and re-signals on an edit
        that changed nothing. Each setter has a typed property that already
        performs the coercion, so the comparison is made where it has happened.
        """
        if current == value:
            return
        self._settings.setValue(key, value)
        self._settings.sync()
        if notify:
            self.changed.emit()


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def _as_bool(raw: object, default: bool) -> bool:
    """Coerce a stored value to bool. INI files hand back `"true"`, not `True`."""
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
    """Coerce a stored value to a float inside `[low, high]`, or the default.

    Clamping on read as well as on write matters: a value edited by hand into
    the store, or left behind by an older build with different limits, must not
    be able to configure the application into a state its own UI cannot express.
    """
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
