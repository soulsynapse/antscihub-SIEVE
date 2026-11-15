"""The File menu's Open Recent as the player draws it: a row a document, its name and when it was
noted over its folder and the video it names. `fill` reads recent's entries and each document's
file for its video; the window hands it the submenu and what opening a path does."""
import json
import os
import time
from datetime import datetime

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QFontMetricsF, QPainter
from PySide6.QtWidgets import QMenu, QWidget, QWidgetAction

from . import recent, theme
from .theme import GAP, HEAD, INK_2, RADIUS

ROW_W, ROW_H = 420, 42      # a recent document's row, px: two lines
LINE_H = 18
INSET = 8
MARK = 14                   # the movie glyph beside a video's name, px


def when_text(when, now):
    """`when` as the row says it against `now`, both as time.time() gives: the hour today, the
    day otherwise, with its year once that is another; "" for None."""
    if when is None:
        return ""
    then, today = datetime.fromtimestamp(when), datetime.fromtimestamp(now)
    days = (today.date() - then.date()).days
    if days == 0:
        return f"today {then:%H:%M}"
    if days == 1:
        return "yesterday"
    return f"{then.day} {then:%b}" if then.year == today.year else f"{then.day} {then:%b %Y}"


def video_of(path):
    """The file name of the video the document at `path` has written in it; "" for none, and for
    a document that will not read."""
    try:
        with open(path, encoding="utf-8") as f:
            video = json.load(f).get("video")
    except (OSError, ValueError, AttributeError):
        return ""
    return os.path.basename(video) if isinstance(video, str) else ""


class Row(QWidget):
    """A recent document's face in `menu`, lit while `action` is the menu's active one, which the
    pointer makes it; a click closes the menus and triggers the action."""

    def __init__(self, action, menu, path, when, video):
        super().__init__(menu)
        self.action, self.menu = action, menu
        self.name, self.folder, self.when, self.video = os.path.basename(path), os.path.dirname(path), when, video
        self.setFixedSize(ROW_W, ROW_H)
        self.setToolTip(path)
        self.setMouseTracking(True)
        menu.hovered.connect(self._relit)

    def _relit(self, *_):
        self.update()

    def enterEvent(self, e):
        self.menu.setActiveAction(self.action)
        self.update()

    def mouseMoveEvent(self, e):
        if self.menu.activeAction() is not self.action:
            self.enterEvent(e)

    def leaveEvent(self, e):
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton or not self.rect().contains(e.position().toPoint()):
            return
        m = self.menu
        while isinstance(m, QMenu):     # before the trigger: opening may ask of unsaved changes, and no menu stays up under that
            m.hide()
            m = m.parentWidget()
        self.action.trigger()

    def paintEvent(self, event):
        del event
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        if self.menu.activeAction() is self.action:
            p.setPen(Qt.NoPen)
            p.setBrush(theme.qgray(theme.layer(3)))
            p.drawRoundedRect(QRectF(self.rect()), RADIUS, RADIUS)
        ui, mono = theme.ui_font(), theme.mono_font()
        w = self.width() - 2 * INSET
        top, low = QRectF(INSET, 3, w, LINE_H), QRectF(INSET, 3 + LINE_H, w, LINE_H)

        def text(r, s, ink, font, align, elide):
            p.setFont(font)
            p.setPen(theme.qgray(ink))
            p.drawText(r, (align | Qt.AlignVCenter).value, QFontMetricsF(font).elidedText(s, elide, r.width()))

        when_w = QFontMetricsF(ui).horizontalAdvance(self.when)
        text(QRectF(top.left(), top.top(), w - when_w - 2 * GAP, LINE_H), self.name, HEAD, ui, Qt.AlignLeft, Qt.ElideRight)
        text(top, self.when, INK_2, ui, Qt.AlignRight, Qt.ElideNone)
        video_w = QFontMetricsF(mono).horizontalAdvance(self.video) + MARK + 4 if self.video else 0
        text(QRectF(low.left(), low.top(), w - video_w - (2 * GAP if self.video else 0), LINE_H), self.folder, INK_2, mono,
             Qt.AlignLeft, Qt.ElideLeft)
        if self.video:
            p.drawPixmap(QPointF(low.right() - video_w, low.top() + (LINE_H - MARK) / 2),
                         theme.glyph("movie", INK_2, MARK, self.devicePixelRatioF()))
            text(low, self.video, INK_2, mono, Qt.AlignRight, Qt.ElideNone)
        p.end()


def fill(menu, opened):
    """Empties `menu` and gives it a Row for each of recent's entries, each calling `opened(path)`
    when chosen, or one line saying there are none. An action's text is its document's path."""
    menu.clear()
    now = time.time()
    for path, when in recent.entries():
        action = QWidgetAction(menu)
        action.setText(path)
        action.setDefaultWidget(Row(action, menu, path, when_text(when, now), video_of(path)))
        action.triggered.connect(lambda _=False, path=path: opened(path))
        menu.addAction(action)
    if menu.isEmpty():
        menu.addAction("No recent documents").setEnabled(False)
