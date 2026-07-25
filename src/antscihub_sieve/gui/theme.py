from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget


# Custom-painted media surfaces
MEDIA_BACKGROUND = QColor("#12151a")
MEDIA_PLACEHOLDER_TEXT = QColor("#aab2bf")
DRAW_PREVIEW_OUTLINE = QColor("#ffd24a")

# Custom-painted isolate timeline
TIMELINE_TRACK_BORDER = QColor("#5b6573")
TIMELINE_TRACK_BACKGROUND = QColor("#20252d")
TIMELINE_EMPTY_TEXT = QColor("#8993a1")
TIMELINE_WINDOW_BORDER = QColor("#60a5fa")
TIMELINE_WINDOW_BACKGROUND = QColor("#2563eb")
TIMELINE_CURSOR = QColor("#fbbf24")


_MENU_BAR_STYLESHEET = """
    QMenuBar { padding: 3px 6px; spacing: 3px; }
    QMenuBar::item { padding: 5px 10px; border-radius: 4px; }
    QMenuBar::item:selected { background: palette(midlight); }
    QMenu { padding: 4px; }
    QMenu::item { padding: 5px 28px 5px 10px; border-radius: 4px; }
    QMenu::item:selected {
        background: palette(highlight);
        color: palette(highlighted-text);
    }
    QMenu::item:disabled { color: palette(mid); }
    QMenu::separator {
        height: 1px;
        background: palette(mid);
        margin: 4px 7px;
    }
"""

_RECENT_LIST_STYLESHEET = """
    QListWidget { border: 0; padding: 1px; }
    QListWidget::item { padding: 3px 8px; border-radius: 4px; }
    QListWidget::item:selected {
        background: palette(highlight);
        color: palette(highlighted-text);
    }
"""

_EXTRACTION_PROGRESS_STYLESHEET = """
    #extractionProgress {
        background: #eff6ff;
        border: 1px solid #60a5fa;
        border-radius: 7px;
    }
"""

_PRIMARY_ACTION_STYLESHEET = """
    QPushButton {
        background: #2563eb;
        color: white;
        border: 1px solid #1d4ed8;
        border-radius: 6px;
        font-size: 15px;
        font-weight: 600;
        padding: 8px 18px;
    }
    QPushButton:hover { background: #1d4ed8; }
    QPushButton:pressed { background: #1e40af; }
    QPushButton:disabled {
        background: #94a3b8;
        border-color: #94a3b8;
    }
"""


def apply_menu_bar_theme(widget: QWidget) -> None:
    widget.setStyleSheet(_MENU_BAR_STYLESHEET)


def apply_recent_list_theme(widget: QWidget) -> None:
    widget.setStyleSheet(_RECENT_LIST_STYLESHEET)


def apply_channels_heading_theme(widget: QWidget) -> None:
    widget.setStyleSheet("font-size: 17px; font-weight: 600;")


def apply_extraction_progress_theme(
    container: QWidget,
    heading: QWidget,
) -> None:
    container.setStyleSheet(_EXTRACTION_PROGRESS_STYLESHEET)
    heading.setStyleSheet("font-weight: 600;")


def apply_primary_action_theme(widget: QWidget) -> None:
    widget.setStyleSheet(_PRIMARY_ACTION_STYLESHEET)
