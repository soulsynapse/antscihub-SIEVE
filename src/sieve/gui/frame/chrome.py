"""What the window wears where no compartment covers it.

Every rule is anchored to the splitter or to a named object, never to a bare
widget class: a plain `QLabel` or `QWidget` selector set on the window reaches
down into whatever the compartments come to hold — surfaces that paint
themselves — and the two stylesheets would then fight over every card.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QWidget

from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, STACK_BG, TEXT, rgb


def stylesheet() -> str:
    return f"""
        QMainWindow, QSplitter {{ background: {rgb(STACK_BG)}; }}
        QSplitter::handle {{ background: {rgb(LINE)}; }}
        QSplitter::handle:horizontal {{ width: 3px; }}
        QSplitter::handle:vertical {{ height: 3px; }}
        QSplitter::handle:hover {{ background: {rgb(ACCENT)}; }}
        #seam {{ background: {rgb(LINE)}; }}
        #timeline {{ background: {rgb(STACK_BG)}; }}
        #timeline QLabel {{ color: {rgb(TEXT)}; }}

        /* The bar sits on the window's ground and closes with the same line a
           seam is made of, so the top boundary reads like the other two. */
        #menubar {{
            background: {rgb(STACK_BG)};
            color: {rgb(TEXT)};
            border-bottom: 1px solid {rgb(LINE)};
            padding: 2px 4px;
        }}
        #menubar::item {{ background: transparent; padding: 4px 10px; }}
        #menubar::item:selected {{ background: {rgb(PANEL_HOT)}; }}
        #menubar::item:pressed {{ background: {rgb(PANEL)}; }}

        /* Dropped menus are panes, not ground: a panel fill inside a hairline,
           the same pairing every card in the compartments will use. */
        QMenu {{
            background: {rgb(PANEL)};
            color: {rgb(TEXT)};
            border: 1px solid {rgb(LINE)};
            padding: 4px 0;
        }}
        QMenu::item {{ padding: 5px 28px 5px 20px; }}
        QMenu::item:selected {{ background: {rgb(PANEL_HOT)}; }}
        QMenu::item:disabled {{ color: {rgb(DIM)}; }}
        QMenu::separator {{
            height: 1px;
            background: {rgb(LINE)};
            margin: 4px 8px;
        }}

        /* Anchored to the class and reaching only into its own label: a dialog
           the frame raises is not a compartment, and nothing inside one is. */
        QMessageBox {{ background: {rgb(PANEL)}; }}
        QMessageBox QLabel {{ color: {rgb(TEXT)}; }}
    """


def darken_title_bar(window: QWidget) -> None:
    """Ask DWM for the dark frame, since Qt does not carry the palette there.

    The title bar is the OS's, not Qt's: without this the window wears the
    system light frame over a dark app whatever the stylesheet says. Attribute
    20 is `DWMWA_USE_IMMERSIVE_DARK_MODE`; on anything that is not a recent
    Windows the call simply fails and the frame stays the platform's.
    """
    if sys.platform != "win32":
        return
    try:
        from ctypes import byref, c_int, windll

        windll.dwmapi.DwmSetWindowAttribute(int(window.winId()), 20, byref(c_int(1)), 4)
    except (OSError, AttributeError, ImportError):
        pass
