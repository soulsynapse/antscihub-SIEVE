"""Driving Qt from a test without pytest-qt: synthetic mouse input, and waiting.

pytest-qt is not installed, so `qtbot` is unavailable and its two services are
re-derived here. It was originally excluded for a reason that has since been
restated — its plugin imports the Qt binding at `pytest_configure`, which broke
the residency assertion Phase 6 made (`tests/gui/conftest.py` on where that went)
— and it stays out now for the ordinary reason a dependency stays out: nothing
here needs it. What is below is two functions and a loop.

Every Qt import is inside a function, which is what lets a bench module import
this one without loading Qt to collect it.

**Input is constructed and handed to the widget's handlers directly** rather
than posted through `QTest.mouseMove`, which needs a real window under a real
cursor and is unreliable on the offscreen platform. The widget code under test
reads only `button()`, `buttons()` and `position()`, all of which are set here
exactly as Qt would. Coordinates are plain floats so a caller need not import
`QPointF` to say where the cursor is.

**Waiting is `processEvents` against a deadline** rather than a nested event
loop. What these tests wait on is a queued signal from the decode thread, which
is delivered by draining the queue; a `QEventLoop` would deliver the same thing
and additionally block forever if the signal never came.
"""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter, sleep
from typing import Any

#: How long a wait pauses between drains. Short enough that a frame arriving
#: mid-sleep is noticed promptly, long enough not to spin a core.
_POLL_SECONDS = 0.002


def _event(kind: Any, x: float, y: float, *, held: bool) -> Any:
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    point = QPointF(x, y)
    return QMouseEvent(
        kind,
        point,
        point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton if held else Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )


def press(widget: Any, x: float, y: float) -> None:
    """Left-button press at `(x, y)` in widget coordinates."""
    from PySide6.QtCore import QEvent

    widget.mousePressEvent(_event(QEvent.Type.MouseButtonPress, x, y, held=True))


def move(widget: Any, x: float, y: float) -> None:
    """Left-button drag to `(x, y)` in widget coordinates."""
    from PySide6.QtCore import QEvent

    widget.mouseMoveEvent(_event(QEvent.Type.MouseMove, x, y, held=True))


def release(widget: Any, x: float, y: float) -> None:
    """Left-button release at `(x, y)` in widget coordinates."""
    from PySide6.QtCore import QEvent

    widget.mouseReleaseEvent(_event(QEvent.Type.MouseButtonRelease, x, y, held=False))


def drag(widget: Any, start: tuple[float, float], end: tuple[float, float]) -> None:
    """Press, move, and release — the full gesture."""
    press(widget, *start)
    move(widget, *end)
    release(widget, *end)


def click(widget: Any, x: float, y: float) -> None:
    """Press and release without travelling."""
    drag(widget, (x, y), (x, y))


def leave(widget: Any) -> None:
    """The cursor leaving the widget, which is what clears a hover readout."""
    from PySide6.QtCore import QEvent

    widget.leaveEvent(QEvent(QEvent.Type.Leave))


def pump() -> None:
    """Deliver whatever is queued right now, without waiting for anything."""
    from PySide6.QtWidgets import QApplication

    QApplication.processEvents()


def wait(milliseconds: float) -> None:
    """Keep delivering events for `milliseconds`.

    Used where the claim is that something does *not* happen: a bare sleep would
    leave the frame in the queue and pass for the wrong reason.
    """
    deadline = perf_counter() + milliseconds / 1000.0
    while perf_counter() < deadline:
        pump()
        sleep(_POLL_SECONDS)


def wait_until(predicate: Callable[[], bool], timeout_ms: float) -> None:
    """Drain the event queue until `predicate` holds, or fail saying it did not."""
    deadline = perf_counter() + timeout_ms / 1000.0
    while perf_counter() < deadline:
        pump()
        if predicate():
            return
        sleep(_POLL_SECONDS)
    pump()
    if not predicate():
        raise AssertionError(f"condition still false after {timeout_ms:.0f} ms")
