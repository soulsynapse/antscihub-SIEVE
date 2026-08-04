"""Secret: what preference categories exist and how picking one on the left
swaps the content on the right.

Not what's inside a category — a category's page owns its own contents.
Nothing outside this file builds the category list or the picker/page
wiring; a new category means a new entry here, not a widget stitched in
from outside.
"""

from __future__ import annotations

import sys
from pathlib import Path

def _find_repo_root(start: Path) -> Path:
    # Walks up to the marker (pyproject.toml) instead of counting parents —
    # a fixed index breaks the moment this file moves to a different depth.
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError(f"no pyproject.toml found above {start}")


_REPO_ROOT = _find_repo_root(Path(__file__).resolve())
if str(_REPO_ROOT) not in sys.path:
    # Same reasoning as app.py: makes running this file directly work the
    # same as running it via -m.
    sys.path.insert(0, str(_REPO_ROOT))

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from proto_sieve.src.sieve.preferences import appearance as appearance_prefs

# Placeholder taxonomy — a Dev category tying into
# sieve/preferences/dev/flags, etc. get added here as they're needed, not
# guessed at now. Appearance already has a real page, built below.
_CATEGORIES = ("General", "Appearance")


def _build_placeholder_page(name: str) -> QWidget:
    return QLabel(f"{name} — nothing here yet")


def _build_appearance_page() -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)

    accent_button = QPushButton("Accent color…")

    def _pick_accent() -> None:
        current = QColor(appearance_prefs.get_appearance().accent)
        chosen = QColorDialog.getColor(current, page, "Accent color")
        if chosen.isValid():
            appearance_prefs.set_appearance(accent=chosen.name())

    accent_button.clicked.connect(_pick_accent)
    layout.addWidget(accent_button)
    layout.addStretch(1)
    return page


class PreferencesWindow(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")

        self._picker = QListWidget(self)
        self._pages = QStackedWidget(self)
        for name in _CATEGORIES:
            self._picker.addItem(name)
            page = _build_appearance_page() if name == "Appearance" else _build_placeholder_page(name)
            self._pages.addWidget(page)

        self._picker.currentRowChanged.connect(self._pages.setCurrentIndex)
        self._picker.setCurrentRow(0)

        layout = QHBoxLayout(self)
        layout.addWidget(self._picker, 1)
        layout.addWidget(self._pages, 3)

        self.resize(480, 320)


if __name__ == "__main__":
    # Standalone smoke test: this window must show something on its own,
    # with no app.py, no menu.py in the loop.
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = PreferencesWindow()
    window.show()
    sys.exit(app.exec())
