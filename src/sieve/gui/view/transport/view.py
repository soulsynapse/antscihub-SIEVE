"""The playhead: a clock, a loop, and a request per frame.

Provisional on purpose. What this looks like is going to be designed properly —
a strip, a signal under it, a window somebody drags — and this is the smallest
thing that plays so the substrate underneath can be felt while that happens. The
*shape* is meant to survive that: a transport that owns a clock and asks for
rows, and a window that answers, is the same arrangement whatever it grows into.

**The playhead follows a clock and the drawing follows the machine.** This is
the one thing here that is not provisional, and it is the explorer's hardest-won
lesson. A loop that advances one row per timer tick plays at whatever rate the
machine can draw, which means the footage runs slow whenever anything else is
happening and nobody can tell whether they are looking at slow behaviour or a
slow computer. So the playhead is computed from elapsed wall time: where the
recording *should* be by now. If the machine drew nothing for a hundred
milliseconds the playhead has still moved, and the frames in between were never
going to be seen.

**Those skipped frames are counted, not queued.** A frame superseded before it
was drawn was never going to be seen, and drawing it costs the one after it
(`docs/decode/ideas.md`). They are a chosen discard rather than waste — the
alternative is not "draw them" but "run slow" — which is why the window charges
them to the ledger as such (ADR-0008).

**It asks and does not act.** `wants` is emitted with a row; what serving one
means is the ladder's and the window's. A transport that reached for a session
would be a second place the tier order lived, and would be reaching for it on
the thread that draws.

**No size hints, `Ignored` policies**, like everything else that updates. The
bottom pane's height is fixed and the strip that will eventually live here must
not argue with it (`docs/findings/2026.08.22-what-froze-the-felt-loop.md`).
"""

from __future__ import annotations

import time

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, TEXT

#: How often the clock is read. Not the frame rate: reading more often than a
#: frame lasts costs nothing and means the playhead lands on the right row
#: sooner after a stall, and reading less often would make the loop stutter on
#: a machine that could have kept up.
TICK_MS = 8

#: The bar under the readout, in pixels. A provisional drawing of where in the
#: window the playhead is, so there is something to look at while playing.
BAR_HEIGHT = 4


class Transport(QWidget):
    """Plays a row range on a loop, asking for one row at a time."""

    #: This row, now. Emitted at most once per tick and only when the row has
    #: actually changed — a request for the frame already up is a serve, a
    #: paint and a scale that produce the picture that was there.
    wants = Signal(int)

    #: Frames the clock passed while the machine was elsewhere. Carried out to
    #: the window rather than counted here, because what a discarded frame *is*
    #: — a cost somebody chose, not waste — is the ledger's vocabulary.
    skipped = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("transport")
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

        self._first = 0
        self._last = 0
        self._fps = 24.0
        self._row = 0
        self._started_at = 0.0
        self._started_row = 0

        self._play = QLabel("")
        self._play.setObjectName("transportplay")
        self._play.setCursor(Qt.CursorShape.PointingHandCursor)
        self._readout = QLabel("nothing open")
        self._readout.setObjectName("transportreadout")
        for label in (self._play, self._readout):
            label.setSizePolicy(QSizePolicy.Policy.Ignored,
                                QSizePolicy.Policy.Ignored)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 6, 12, 6 + BAR_HEIGHT)
        row.setSpacing(12)
        row.addWidget(self._play)
        row.addWidget(self._readout, 1)

        self._clock = QTimer(self)
        self._clock.setInterval(TICK_MS)
        self._clock.timeout.connect(self._advance)

        palette.CHANGED.connect(self._restyle)
        metrics.CHANGED.connect(self._restyle)
        self._restyle()

    # -- what it is playing ----------------------------------------------
    def follow(self, first: int, last: int, fps: float) -> None:
        """Loop `[first, last)` at `fps`. Does not start playing.

        The rate is the *recording's*, handed in rather than assumed, because
        a playhead that ran at some fixed rate would be showing the behaviour
        at a speed nobody recorded it at — and the whole subject here is how
        fast things move.
        """
        self._first = max(0, first)
        self._last = max(self._first + 1, last)
        self._fps = fps if fps > 0 else 24.0
        self._row = self._first
        self._rebase()
        self._draw_readout()
        self.update()

    def playing(self) -> bool:
        return self._clock.isActive()

    def play(self) -> None:
        if self._last <= self._first:
            return
        self._rebase()
        self._clock.start()
        self._draw_readout()

    def pause(self) -> None:
        self._clock.stop()
        self._draw_readout()

    def toggle(self) -> None:
        self.pause() if self.playing() else self.play()

    def at(self) -> int:
        return self._row

    def show_at(self, row: int) -> None:
        """Put the playhead here without asking for it.

        For the window to say where the picture actually is, which is not
        always where the playhead is: a hold leaves the last frame up, and a
        readout that claimed otherwise would be the interface lying about
        which instant is on screen.
        """
        self._row = row
        self._draw_readout()
        self.update()

    # -- the clock -------------------------------------------------------
    def _rebase(self) -> None:
        """Start counting elapsed time from here.

        Called on play and on a new window, so a pause does not leave the
        playhead owing the loop every frame that went by while it was stopped.
        """
        self._started_at = time.perf_counter()
        self._started_row = self._row

    def _advance(self) -> None:
        elapsed = time.perf_counter() - self._started_at
        span = self._last - self._first
        # where the recording should be by now, not one row on from wherever
        # it got to. That is the whole difference between playing at the
        # footage's rate and playing at the machine's.
        ahead = int(elapsed * self._fps)
        row = self._first + (self._started_row - self._first + ahead) % span
        if row == self._row:
            return
        passed = (row - self._row) % span
        if passed > 1:
            self.skipped.emit(passed - 1)
        self._row = row
        self._draw_readout()
        self.update()
        self.wants.emit(row)

    # -- what it looks like, for now --------------------------------------
    def _draw_readout(self) -> None:
        if self._last <= self._first:
            self._readout.setText("nothing open")
            self._play.setText("")
            return
        span = self._last - self._first
        seconds = (self._row - self._first) / self._fps
        self._play.setText("Pause" if self.playing() else "Play")
        self._readout.setText(
            f"frame {self._row}  ·  {seconds:5.2f}s of "
            f"{span / self._fps:.1f}s  ·  {self._fps:.2f} fps"
            f"  ·  {self._first}–{self._last}")

    def mousePressEvent(self, event) -> None:
        del event
        self.toggle()

    def sizeHint(self) -> QSize:
        return QSize()

    def minimumSizeHint(self) -> QSize:
        return QSize()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), PANEL)
        bar = self.rect().adjusted(0, self.height() - BAR_HEIGHT, 0, 0)
        painter.fillRect(bar, LINE)
        if self._last > self._first:
            through = (self._row - self._first) / (self._last - self._first)
            painter.fillRect(bar.x(), bar.y(),
                             max(1, int(bar.width() * through)),
                             bar.height(), ACCENT)
        painter.end()

    def _restyle(self) -> None:
        # sized from the text rather than a number: the whole application
        # scales with the size preference, and a strip pinned to a fixed pixel
        # height would be the one thing that did not move with it.
        self.setFixedHeight(metrics.pt('name') * 3 + BAR_HEIGHT)
        self.setStyleSheet(
            f"#transportplay {{ color: {TEXT.name()}; "
            f"font-size: {metrics.pt('name')}pt; }}"
            f"#transportreadout {{ color: {DIM.name()}; "
            f"font-size: {metrics.pt('gloss')}pt; }}"
        )
        self.update()
