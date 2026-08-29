"""Stylesheet and title-bar dressing for the window chrome.

Selectors target the splitter or named objects, never bare widget classes.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QWidget

from sieve.gui import palette
from sieve.gui.palette import ACCENT, LINE, PANEL, PANEL_HOT, STACK_BG, TEXT, rgb
from sieve.gui.primitives import menu


def stylesheet() -> str:
    return f"""
        QMainWindow, QSplitter {{ background: {rgb(STACK_BG)}; }}
        QSplitter::handle {{ background: {rgb(LINE)}; }}
        QSplitter::handle:horizontal {{ width: 3px; }}
        QSplitter::handle:vertical {{ height: 3px; }}
        QSplitter::handle:hover {{ background: {rgb(ACCENT)}; }}
        #seam {{ background: {rgb(LINE)}; }}
        #bottom {{ background: {rgb(STACK_BG)}; }}
        #bottom QLabel {{ color: {rgb(TEXT)}; }}

        #menubar {{
            background: {rgb(STACK_BG)};
            color: {rgb(TEXT)};
            border-bottom: 1px solid {rgb(LINE)};
            padding: 2px 4px;
        }}
        #menubar::item {{ background: transparent; padding: 4px 10px; }}
        #menubar::item:selected {{ background: {rgb(PANEL_HOT)}; }}
        #menubar::item:pressed {{ background: {rgb(PANEL)}; }}

        {menu.sheet()}

        QMessageBox {{ background: {rgb(PANEL)}; }}
        QMessageBox QLabel {{ color: {rgb(TEXT)}; }}
    """


def dress_title_bar(window: QWidget) -> None:
    """Toggle DWM dark-mode title bar (attr 20) to match the palette."""
    if sys.platform != "win32":
        return
    try:
        from ctypes import byref, c_int, windll

        dark = c_int(1 if palette.current().dark else 0)
        windll.dwmapi.DwmSetWindowAttribute(int(window.winId()), 20, byref(dark), 4)
    except (OSError, AttributeError, ImportError):
        pass
