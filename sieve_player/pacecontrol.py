"""The pace control: a pace.Figure drawn as one button, for the player's header and the monitor's.
It reads the figure it is handed and the theme, and nothing of the window either sits in.
"""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton

from . import theme
from .pace import clock
from .theme import GAP, ROW_H


class PaceControl(QAbstractButton):
    """A pace.Figure as one control, drawn and not written: the lane's glyph, the rate as a multiple
    of realtime, a bar and a time. The bar's width is the range and its filled part the rows done,
    cut by what they were: those a store held dim, those that ran bright, those that read a bake
    hatched, in that order and not at the rows' places, the figure holding counts. The time is under
    the glyph of what it is, the clip at this rate, the clip walk's rest or what it took, and a dash
    where the figure gives none. The tooltip is the figure's words, then `hint`, what a press does;
    without one it does not show as pressable. Its width never follows its text."""
    BAR_W, BAR_H, EDGE = 140, 8, 6
    LANES = {"window": "brackets-contain", "clip": "movie"}
    TIMES = {"takes": "clock", "left": "hourglass", "took": "circle-check"}
    HELD = 105      # a held row's gray, between the bar's ground and a row that ran

    def __init__(self, hint="", parent=None):
        super().__init__(parent)
        self.figure, self.hint = None, hint
        self.setFont(theme.mono_font())
        fm = QFontMetrics(self.font())
        self._rate_w, self._time_w = fm.horizontalAdvance("00.0×"), fm.horizontalAdvance("0:00:00")
        self.setFixedSize(3 * self.EDGE + 2 * theme.GLYPH + self._rate_w + self.BAR_W + 2 * GAP + 4 + self._time_w, ROW_H)
        self.setAttribute(Qt.WA_Hover, bool(hint))
        if hint:
            self.setCursor(Qt.PointingHandCursor)

    def set_figure(self, figure):
        """`figure`, a pace.Figure, or None for no walk to show."""
        self.figure = figure
        self.setToolTip("" if figure is None else figure.words() + ("\n" + self.hint if self.hint else ""))
        self.update()

    def paintEvent(self, event):
        del event
        f = self.figure
        if f is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        base = theme.layer(theme.depth_of(self) + 1)
        if self.hint and self.underMouse() and self.isEnabled():
            p.setPen(QPen(theme.qgray(base + theme.LINE_LIFT).lighter(theme.HOVER_EDGE), 1))
            p.setBrush(theme.qgray(base + theme.HOVER_LIFT))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), theme.RADIUS, theme.RADIUS)
        ratio, h, top = self.devicePixelRatioF(), self.height(), (self.height() - theme.GLYPH) / 2
        dim = theme.INK_2 - 50
        x = self.EDGE
        p.drawPixmap(QPointF(x, top), theme.glyph(self.LANES[f.lane], theme.INK_2, theme.GLYPH, ratio))
        x += theme.GLYPH + self.EDGE
        p.setFont(self.font())
        p.setPen(theme.qgray(theme.INK if f.multiple is not None else dim))
        rate = "–" if f.multiple is None else f"{f.multiple:.1f}×" if f.multiple < 100 else f"{f.multiple:.0f}×"
        p.drawText(QRectF(x, 0, self._rate_w, h), Qt.AlignRight | Qt.AlignVCenter, rate)
        x += self._rate_w + GAP
        bar = QRectF(x, (h - self.BAR_H) / 2, self.BAR_W, self.BAR_H)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.fillRect(bar, theme.qgray(theme.GROUND - theme.STEP))
        at = bar.left()
        for rows, brush in ((f.held, theme.qgray(self.HELD)), (f.ran, theme.qgray(theme.INK)), (f.served, None)):
            w = self.BAR_W * rows / f.total if f.total else 0
            if brush is None:
                p.fillRect(QRectF(at, bar.top(), w, self.BAR_H), theme.qgray(self.HELD - 45))
                brush = QBrush(theme.qgray(theme.INK), Qt.BDiagPattern)
            p.fillRect(QRectF(at, bar.top(), w, self.BAR_H), brush)
            at += w
        p.setPen(QPen(theme.qgray(base + theme.LINE_LIFT), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(bar.adjusted(0, 0, -1, -1))
        p.setRenderHint(QPainter.Antialiasing, True)
        x += self.BAR_W + GAP
        name = self.TIMES.get(f.what, "clock" if f.lane == "window" else "hourglass")
        p.drawPixmap(QPointF(x, top), theme.glyph(name, theme.INK_2 if f.what else dim, theme.GLYPH, ratio))
        x += theme.GLYPH + 4
        p.setPen(theme.qgray(theme.INK if f.what else dim))
        p.drawText(QRectF(x, 0, self._time_w, h), Qt.AlignLeft | Qt.AlignVCenter, clock(f.seconds) if f.what else "–")
        p.end()

    def event(self, e):
        if e.type() in (e.Type.HoverEnter, e.Type.HoverLeave):
            self.update()
        return super().event(e)
