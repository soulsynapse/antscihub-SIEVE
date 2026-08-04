"""Secret: what dropdown menus exist and what each entry does.

Not the window itself — ``app.py`` owns the window, this module only ever
populates its menu bar. Adding or renaming an entry must not touch app.py;
changing what the window is otherwise made of must never touch this file.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow

from proto_sieve.src.sieve.gui.windows import PreferencesWindow


def build_menu_bar(window: QMainWindow) -> None:
    file_menu = window.menuBar().addMenu("&File")
    file_menu.addAction("E&xit", window.close)

    edit_menu = window.menuBar().addMenu("&Edit")
    edit_menu.addAction("Undo")
    edit_menu.addAction("Redo")

    settings_menu = window.menuBar().addMenu("&Settings")
    settings_menu.addAction("Preferences", lambda: PreferencesWindow(window).exec())
