"""The Dev menu: what helps build SIEVE and is no part of using it. Everything under it lives in
this package and nowhere else, so the junk stays in one drawer.

`install(window)` adds the menu to the window's bar. Each entry opens its own window at most once;
the windows are kept on the main window so they outlive the menu action.
"""
from __future__ import annotations

from PySide6.QtWidgets import QMainWindow


def install(window: QMainWindow) -> None:
    menu = window.menuBar().addMenu("Dev")
    menu.addAction("Icon reference…", lambda: _show(window, "icons"))


def _show(window: QMainWindow, key: str) -> None:
    opened = window.__dict__.setdefault("_dev_windows", {})
    w = opened.get(key)
    if w is None:
        if key == "icons":
            from .reference.icons import Icons
            w = Icons(window)
        opened[key] = w
    w.show()
    w.raise_()
    w.activateWindow()
