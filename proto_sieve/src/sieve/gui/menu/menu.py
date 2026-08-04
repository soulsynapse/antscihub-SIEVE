"""Secret: what dropdown menus exist, and which of the window's public
methods each entry calls.

Not the window itself — ``app.py`` owns the window and what each verb
(``load_project``, ``save_pipeline``, ``open_history``, ``close``) actually
does; this module only ever wires an entry to one. Renaming or reordering
entries, or wiring one to a method ``app.py`` already exposes, must not
touch app.py; changing what the window is otherwise made of must never touch
this file. A genuinely new verb still needs a new method on ``MainWindow``
first — this file only calls, it never defines.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow

from proto_sieve.src.sieve.gui.windows import PreferencesWindow


def build_menu_bar(window: QMainWindow) -> None:
    file_menu = window.menuBar().addMenu("&File")
    file_menu.addAction("&Load Project…", window.load_project)
    file_menu.addAction("&Save Pipeline", window.save_pipeline)
    file_menu.addSeparator()
    file_menu.addAction("Project &History…", window.open_history)
    file_menu.addSeparator()
    file_menu.addAction("E&xit", window.close)

    edit_menu = window.menuBar().addMenu("&Edit")
    edit_menu.addAction("Undo")
    edit_menu.addAction("Redo")

    settings_menu = window.menuBar().addMenu("&Settings")
    settings_menu.addAction("Preferences", lambda: PreferencesWindow(window).exec())
