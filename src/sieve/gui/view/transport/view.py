"""The transport: a control row over the strip, in the bottom pane.

Ported from `mockup/mockup.py`'s `build_timeline`. It is not a `View`: the
bottom pane is `BOTTOM_HEIGHT` tall and a titled head band would take a third
of it, and `Pane` already draws the ground and the border a view would have
brought.

**Rows and not subpanes.** ADR-0002 gives the bottom pane the horizontal axis
only — `build_bottom` anchors `Side.LEFT` and `Side.RIGHT` — so a control row
*above* a strip cannot be a subpane and is a row inside the pane's body. A
subpane down here would be a fixed gutter at one end, which is a different
thing and not this.

**Space, because the arrows are spent.** ADR-0003 puts ← and → on walking the
swipe track and reserves ↑/↓ for whatever selection the position in view owns,
so neither pair is free for a transport. Space is the play key and the frame
steps take `,` and `.`, which is what every editor this audience already uses
does with them.

Playback advances by *listed position*, never by a clock: the extent is what
the source says exists, and a wall clock walking a timebase that a folder of
stills invented would be inventing a frame rate to go with it. What the timer
period means is therefore "how fast to step", not "real time".
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sieve.contract.edges import Access
from sieve.gui import metrics
from sieve.gui.primitives import Button
from sieve.gui.view.transport.bar import Strip

#: Step period while playing. A placeholder rate, and honestly so: the tier
#: that makes a real one meetable is not built, and a transport claiming 24 fps
#: while a read costs 350 ms would be a number about nothing.
STEP_MS = 40


class Transport(QWidget):
    """Play, step, scrub. Says where the user pointed; reads nothing itself."""

    #: a guess — cheap answers only, and a stale picture beats a stall
    dragged = Signal(int)
    #: a commitment — this one may be paid for
    released = Signal(int)
    #: a playback step; neither of the above
    stepped = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("transport")
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._positions: tuple[int, ...] = ()

        self.strip = Strip()
        self.strip.dragged.connect(self.dragged)
        self.strip.released.connect(self.released)

        self.play = Button("Play", small=True)
        self.play.setFixedWidth(56)
        self.play.setToolTip("Play / pause (Space)")
        self.play.clicked.connect(self.toggle_play)

        self.where = QLabel("")
        self.where.setTextFormat(Qt.TextFormat.PlainText)
        self.where.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        # A width fixed from a template rather than from the text. This label
        # changes every step, and one whose hint follows its content is what
        # the freeze hunt measured nudging the splitter and resizing the video
        # every few seconds. Ignored was the first attempt and is worse: with
        # a stretch beside it the label is handed nothing and disappears.
        self._remeasure()
        metrics.CHANGED.connect(self._remeasure)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(self.play)
        row.addStretch(1)
        row.addWidget(self.where)

        column = QVBoxLayout(self)
        column.setContentsMargins(8, 2, 8, 4)
        column.setSpacing(2)
        column.addLayout(row)
        column.addWidget(self.strip)

        self._timer = QTimer(self)
        self._timer.setInterval(STEP_MS)
        self._timer.timeout.connect(self._tick)
        self.show_source((), (), Access.RANDOM)

    def _remeasure(self) -> None:
        """Width enough for the longest thing this ever says, and no more."""
        sample = "888,888 / 888,888   pts 8,888,888,888"
        self.where.setFixedWidth(
            QFontMetrics(self.where.font()).horizontalAdvance(sample) + 8
        )

    # -- what it is about --------------------------------------------------

    def show_source(
        self,
        positions: tuple[int, ...],
        starts: tuple[int, ...] = (),
        access: Access = Access.RANDOM,
    ) -> None:
        """Point the transport at an open source, or at nothing."""
        self.stop()
        self._positions = positions
        self.strip.show_source(positions, starts, access)
        self.play.setEnabled(bool(positions))
        if positions:
            self.strip.show_playhead(positions[0])
        self._say()

    def show_playhead(self, position: int | None) -> None:
        self.strip.show_playhead(position)
        self._say()

    def _say(self) -> None:
        mapping = self.strip.geometry_now()
        at = self.strip.playhead()
        if at is None or mapping.empty:
            self.where.setText("")
            return
        self.where.setText(
            f"{mapping.ordinal(at) + 1:,} / {mapping.count:,}   pts {at:,}"
        )

    # -- playing -----------------------------------------------------------

    def playing(self) -> bool:
        return self._timer.isActive()

    def toggle_play(self) -> None:
        self.stop() if self.playing() else self.start()

    def start(self) -> None:
        if not self._positions:
            return
        self.play.setText("Pause")
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self.play.setText("Play")

    def step(self, delta: int) -> None:
        """Move by *delta* listed positions and ask for what is there."""
        if not self._positions:
            return
        mapping = self.strip.geometry_now()
        at = self.strip.playhead()
        index = 0 if at is None else mapping.ordinal(at) + delta
        if not 0 <= index < len(self._positions):
            self.stop()
            return
        position = self._positions[index]
        self.strip.show_playhead(position)
        self._say()
        self.stepped.emit(position)

    def _tick(self) -> None:
        self.step(1)
