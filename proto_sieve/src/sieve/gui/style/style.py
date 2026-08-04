"""Secret: how a value in ``preferences.Appearance`` becomes Qt's styling.

Not what the values are or where they're set — ``sieve/preferences`` owns
that; this file only ever reads ``preferences.get_appearance()``. Not any
one widget's look. Nothing outside this file constructs a ``QColor``,
writes a hex code, or calls ``setStyleSheet`` — a widget that wants to
look different needs a new role here, not a local override.
"""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from proto_sieve.src.sieve.preferences.appearance import Appearance, get_appearance

# Roles let a widget opt into a distinct look via ``tag()`` instead of a
# subclass or a local ``setStyleSheet`` — the QSS below is still the only
# place a color gets attached to one.
ROLE_BAR = "bar"


def tag(widget: QWidget, role: str) -> None:
    widget.setProperty("role", role)


def bar_height() -> int:
    return get_appearance().bar_height


def _build_qss(a: Appearance) -> str:
    return f"""
QMainWindow, QWidget {{
    background-color: {a.background};
    color: {a.text};
    font-size: 13px;
}}

QLabel {{
    background-color: {a.surface};
    color: {a.text_muted};
    padding: {a.spacing_unit}px;
}}

QLabel[role="bar"] {{
    background-color: {a.background};
    border-top: 1px solid {a.border};
    border-bottom: 1px solid {a.border};
}}

QListWidget {{
    background-color: {a.surface};
    border: 1px solid {a.border};
    border-radius: {a.radius}px;
    padding: {a.spacing_unit // 2}px;
}}

QListWidget::item {{
    padding: {a.spacing_unit // 2}px;
    border-radius: {a.radius}px;
}}

QListWidget::item:selected {{
    background-color: {a.accent};
    color: {a.text};
}}

QMenuBar {{
    background-color: {a.surface};
    color: {a.text};
    border-bottom: 1px solid {a.border};
    padding: {a.spacing_unit // 4}px;
}}

QMenuBar::item {{
    padding: {a.spacing_unit // 2}px {a.spacing_unit}px;
    border-radius: {a.radius}px;
}}

QMenuBar::item:selected {{
    background-color: {a.accent};
}}

QMenu {{
    background-color: {a.surface};
    color: {a.text};
    border: 1px solid {a.border};
}}

QMenu::item:selected {{
    background-color: {a.accent};
}}

QSplitter::handle {{
    background-color: {a.border};
}}
"""


_DWMWA_CAPTION_COLOR = 35
_DWMWA_TEXT_COLOR = 36


def _colorref(hex_color: str) -> int:
    # DWM wants a COLORREF: 0x00BBGGRR, the reverse byte order of the hex
    # strings above.
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return r | (g << 8) | (b << 16)


def apply_title_bar(window: QMainWindow) -> None:
    """The native title bar is OS chrome, not a Qt widget — QSS above never
    reaches it. Windows 11 alone exposes a DWM call to recolor it; every
    other platform leaves this a no-op rather than fake the effect."""
    if sys.platform != "win32":
        return

    a = get_appearance()
    hwnd = int(window.winId())
    dwmapi = ctypes.windll.dwmapi
    for attribute, hex_color in (
        (_DWMWA_CAPTION_COLOR, a.background),
        (_DWMWA_TEXT_COLOR, a.text),
    ):
        color = ctypes.c_int(_colorref(hex_color))
        dwmapi.DwmSetWindowAttribute(
            hwnd, attribute, ctypes.byref(color), ctypes.sizeof(color)
        )


def apply(app: QApplication) -> None:
    app.setStyleSheet(_build_qss(get_appearance()))


if __name__ == "__main__":
    # Standalone smoke test: a bare window must pick up the style on its
    # own, with no app.py, no layout, no other widget in the loop.
    import sys

    from PySide6.QtWidgets import QLabel

    app = QApplication(sys.argv)
    apply(app)
    label = QLabel("style smoke test")
    label.resize(300, 100)
    label.show()
    sys.exit(app.exec())
