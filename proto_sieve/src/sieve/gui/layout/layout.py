"""Secret: where and how big the chunky parts of the main window go.

Not the subparts themselves — each ``canvas/`` and ``control/`` entry owns
its own insides. Not other windows — ``gui/windows/`` entries own their own
layout too. This module only ever touches the main window's position and
size: splitter proportions, window geometry. Swapping what fills a slot
must not touch this file; changing where a slot sits or how big it starts
must never touch a subpart's file.

Two ways to assemble a screen. ``compose`` is the original, single-screen
frame (still what a standalone smoke test reaches for — no ``app.py``, no
sliding, in the loop): ``canvas`` and ``control`` split evenly, both fixed
for the container's lifetime.

``compose_split`` is what ``app.py`` actually uses, and it does not slide
canvas and control together — an earlier version did (two whole screens as
positions in one sliding container), and it looked wrong: the canvas isn't
a "screen", it's a single view that should just update to match whichever
control is current. So the middle band is a static split between
``CanvasSlot`` (a single already-built widget on the left, swapped in
place with no animation whenever the caller has a new one) and a
``gui/breadcrumb_stack.BreadcrumbStack`` on the right (one already-built
control widget per position — drilling in collapses the one you're leaving
to a labeled bar rather than sliding it away). Only the right side
animates; the left side is told to update, not animated to it.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QMainWindow, QSizePolicy, QSplitter, QVBoxLayout, QWidget

from proto_sieve.src.sieve.gui.breadcrumb_stack import BreadcrumbStack
from proto_sieve.src.sieve.preferences.dev import flags

_WINDOW_WIDTH = 960
_WINDOW_HEIGHT = 540

_FIXED_POLICIES = (QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)
_QWIDGETSIZE_MAX = 16777215  # Qt's "unbounded" sentinel for maximumHeight()/Width()


def _require_layout_section(widget: QWidget) -> None:
    """The contract a widget must meet to go into the middle, horizontally
    split band: it must let the splitter own its width. Two ways a widget
    can silently break that, both checked here — a Fixed/Maximum horizontal
    policy declares it outright, but a nominally Preferred widget can still
    force the same outcome by fixing a numeric floor Qt honors regardless
    of policy."""
    policy = widget.sizePolicy().horizontalPolicy()
    if policy in _FIXED_POLICIES:
        raise TypeError(
            f"{widget.__class__.__name__} has horizontal size policy "
            f"{policy.name} — a layout section must accept the width the "
            "splitter assigns it, not fix its own."
        )

    half_width = _WINDOW_WIDTH // 2
    min_width = max(widget.minimumWidth(), widget.minimumSizeHint().width())
    if min_width > half_width:
        raise TypeError(
            f"{widget.__class__.__name__} has a minimum width of "
            f"{min_width}px, more than its {half_width}px share of a "
            f"{_WINDOW_WIDTH}px window — a layout section must fit inside "
            "the split, not force it wider."
        )


def _require_fixed_bar(widget: QWidget) -> None:
    """The inverse contract, for the bar above and below the middle band:
    it must own a bounded height and not reach for the middle band's space.
    Checked on ``minimumHeight()``/``maximumHeight()`` directly, not
    ``sizePolicy()`` — ``setFixedHeight()`` (the normal way to build one of
    these) sets those bounds equal but leaves the vertical policy at its
    default ``Preferred``, so a policy-only check would reject the exact
    widget this contract exists to allow. Same lesson as the min-width gap
    in ``_require_layout_section``: policy is a declaration, not the fact."""
    min_height = widget.minimumHeight()
    max_height = widget.maximumHeight()
    if max_height >= _QWIDGETSIZE_MAX or min_height != max_height:
        raise TypeError(
            f"{widget.__class__.__name__} has no fixed height (min="
            f"{min_height}, max={max_height}) — a fixed bar must set an "
            "equal, bounded minimum and maximum height, e.g. via "
            "setFixedHeight(), not stretch into the middle band's space."
        )


class CanvasSlot(QWidget):
    """The static, non-sliding left side of the split — one already-built
    widget at a time, swapped in place with no animation. Content must meet
    the same layout-section contract as a control screen (checked here, not
    left to the caller) since it ends up in the same splitter."""

    def __init__(self, initial: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        _require_layout_section(initial)
        self._current = initial
        self._layout.addWidget(initial)

    def set_content(self, widget: QWidget) -> None:
        _require_layout_section(widget)
        old = self._current
        self._layout.removeWidget(old)
        old.setParent(None)
        old.deleteLater()
        self._current = widget
        self._layout.addWidget(widget)
        # Same reasoning as BreadcrumbStack.replace_pane: adding a widget to
        # an already-visible tree does not itself make the widget visible.
        widget.show()


def _split(left: QWidget, right: QWidget) -> QSplitter:
    """The draggable, evenly-sized divider shared by ``build_screen`` and
    ``compose_split`` — the only difference between the two is what ends up
    on each side (two fixed widgets vs. a ``CanvasSlot``/``BreadcrumbStack``
    pair)."""
    splitter = QSplitter(Qt.Orientation.Horizontal)
    splitter.addWidget(left)
    splitter.addWidget(right)
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 1)
    # setSizes() only scales its argument against the splitter's *current*
    # width — and at this point (unshown, unparented) that's 0, so a ratio
    # like [1, 1] is taken as literal pixels, collapses to nothing, and
    # first show falls back to sizeHint()-driven allocation instead (the
    # same failure mode as the video-collapse bug). Passing real pixel
    # values matching the window size this module controls sidesteps that.
    splitter.setSizes([_WINDOW_WIDTH // 2, _WINDOW_WIDTH // 2])
    return splitter


def build_screen(canvas: QWidget, control: QWidget) -> QWidget:
    """The canvas|control split for ``compose``'s single, non-sliding
    screen. Not used by ``compose_split`` — there, canvas and control are
    two independent slots, not one paired screen."""
    _require_layout_section(canvas)
    _require_layout_section(control)
    return _split(canvas, control)


def _assemble(top: QWidget, middle: QWidget, bottom: QWidget) -> QWidget:
    """``top`` and ``bottom`` span the full width at a fixed height; the
    middle band absorbs whatever vertical space is left. The dividers —
    top edge and bottom edge of the middle band — trace an I regardless of
    what's inside the middle band."""
    _require_fixed_bar(top)
    _require_fixed_bar(bottom)

    container = QWidget()
    rows = QVBoxLayout(container)
    rows.setContentsMargins(0, 0, 0, 0)
    rows.setSpacing(0)
    rows.addWidget(top)
    rows.addWidget(middle, 1)  # the only row that absorbs extra vertical space
    rows.addWidget(bottom)
    return container


def compose(top: QWidget, canvas: QWidget, control: QWidget, bottom: QWidget) -> QWidget:
    """Single-screen frame: ``top``/``bottom`` around one ``build_screen``
    middle band, instantly swapped in and out by whoever owns the central
    widget. ``app.py`` no longer uses this for its own screens (see
    ``compose_split``) — kept for standalone smoke tests that want a frame
    with no sliding, no app.py, in the loop."""
    return _assemble(top, build_screen(canvas, control), bottom)


def compose_split(
    top: QWidget, canvas_slot: CanvasSlot, control_screens: list[tuple[str, QWidget]], bottom: QWidget
) -> tuple[QWidget, BreadcrumbStack]:
    """Same ``top``/``bottom`` frame as ``compose``, but the middle band
    splits a static ``CanvasSlot`` (left, swapped in place, no animation)
    from a ``BreadcrumbStack`` over ``control_screens`` — (label, widget)
    pairs — on the right. Meant to be called once, at window construction;
    the returned container is set as the central widget once, and the
    returned ``BreadcrumbStack`` handle is what the caller keeps to later
    swap a position's contents (``replace_pane``) and drill to it
    (``set_current``) — the caller updates ``canvas_slot`` (``set_content``)
    alongside each such switch, but that update is the caller's to
    sequence, not this function's."""
    for _, screen in control_screens:
        _require_layout_section(screen)

    control = BreadcrumbStack(control_screens)
    return _assemble(top, _split(canvas_slot, control), bottom), control


def _move_to_dev_monitor(window: QMainWindow) -> None:
    if flags.MONITOR_INDEX is None:
        return
    screens = QGuiApplication.screens()
    if not 0 <= flags.MONITOR_INDEX < len(screens):
        raise ValueError(
            f"SIEVE_DEV_MONITOR={flags.MONITOR_INDEX} but only "
            f"{len(screens)} screen(s) detected"
        )
    window.move(screens[flags.MONITOR_INDEX].geometry().topLeft())


def size_window(window: QMainWindow) -> None:
    # A starting size still matters even though the window opens maximized:
    # it's what showMaximized() restores to if the user un-maximizes.
    window.resize(_WINDOW_WIDTH, _WINDOW_HEIGHT)
    _move_to_dev_monitor(window)
    window.showMaximized()


if __name__ == "__main__":
    # Standalone smoke test: a canvas (the video player) on the left, a
    # control (pipeline steps) on the right, with no app.py in the loop.
    import sys
    from pathlib import Path

    def _find_repo_root(start: Path) -> Path:
        # Walks up to the marker (pyproject.toml) instead of counting
        # parents — a fixed index breaks the moment this file moves depth.
        for candidate in (start, *start.parents):
            if (candidate / "pyproject.toml").is_file():
                return candidate
        raise RuntimeError(f"no pyproject.toml found above {start}")

    _repo_root = _find_repo_root(Path(__file__).resolve())
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

    from PySide6.QtWidgets import QApplication, QLabel

    from proto_sieve.src.sieve.gui import style
    from proto_sieve.src.sieve.gui.canvas.video_player import VideoPlayer
    from proto_sieve.src.sieve.gui.control.pipeline import PipelinePanel
    from proto_sieve.src.sieve.pipeline import Pipeline, Step

    video_path = _repo_root / "video-test" / "rep3_intermittent_crop.MP4"
    pipeline = Pipeline(
        source="rep3_intermittent_crop",
        steps=(Step(tool="crop", params={"y0": 0, "y1": 200, "x0": 0, "x1": 200}),),
    )

    app = QApplication(sys.argv)
    canvas = VideoPlayer()
    canvas.open(video_path)

    top = QLabel("top")
    top.setFixedHeight(style.bar_height())
    bottom = QLabel("bottom")
    bottom.setFixedHeight(style.bar_height())

    window = QMainWindow()
    window.setCentralWidget(compose(top, canvas, PipelinePanel(pipeline), bottom))
    size_window(window)
    window.show()
    sys.exit(app.exec())
