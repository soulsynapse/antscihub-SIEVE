"""Secret: where and how big the chunky parts of the main window go.

Not the subparts themselves — each ``canvas/`` and ``control/`` entry owns
its own insides. Not other windows — ``gui/windows/`` entries own their own
layout too. This module only ever touches the main window's position and
size: splitter proportions, window geometry. Swapping what fills a slot
must not touch this file; changing where a slot sits or how big it starts
must never touch a subpart's file.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QMainWindow, QSizePolicy, QSplitter, QVBoxLayout, QWidget

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


def compose(top: QWidget, canvas: QWidget, control: QWidget, bottom: QWidget) -> QWidget:
    """``top`` and ``bottom`` span the full width at a fixed height; the
    middle band splits ``canvas`` and ``control`` evenly. The dividers —
    top edge and bottom edge of the middle band, plus the vertical split
    inside it — trace an I."""
    _require_fixed_bar(top)
    _require_fixed_bar(bottom)
    _require_layout_section(canvas)
    _require_layout_section(control)

    middle = QSplitter(Qt.Orientation.Horizontal)
    middle.addWidget(canvas)
    middle.addWidget(control)
    middle.setStretchFactor(0, 1)
    middle.setStretchFactor(1, 1)
    # setSizes() only scales its argument against the splitter's *current*
    # width — and at this point (unshown, unparented) that's 0, so a ratio
    # like [1, 1] is taken as literal pixels, collapses to nothing, and
    # first show falls back to sizeHint()-driven allocation instead (the
    # same failure mode as the video-collapse bug). Passing real pixel
    # values matching the window size this module controls sidesteps that.
    middle.setSizes([_WINDOW_WIDTH // 2, _WINDOW_WIDTH // 2])

    container = QWidget()
    rows = QVBoxLayout(container)
    rows.setContentsMargins(0, 0, 0, 0)
    rows.setSpacing(0)
    rows.addWidget(top)
    rows.addWidget(middle, 1)  # the only row that absorbs extra vertical space
    rows.addWidget(bottom)
    return container


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
