"""The horizontal slider — the control the interactive loop exists for.

Lifted from `view/preferences/minor_visuals.py`, which is a different route than
`button.py` and `field.py` took and worth saying so: those two were settled ahead
of a view asking, because emphasis and focus are budgets spent across the whole
application. A slider is not that. This one is here because a view had already
built it, `mockup/paper_primitives.py` had settled the same shape a second time,
and the pane this project is actually for — drag a threshold, watch the graphs
refill — is a third. Three drawings of one picture is when a shape moves up, and
the preferences section keeps the part that is its own: what its rows are called,
what they are for, and which number is stored versus which is shown.

Three claims come with it.

The wheel is refused. A `QSlider` takes the wheel whether or not it has focus, so
a user rolling down a scroll to reach the last row changes every setting they
pass on the way, with no gesture anywhere in that saying they meant to touch any
of them. Refused on the slider and not on whatever holds it, because the child is
what the event reaches first and a parent cannot decline on its behalf; ignoring
it is what sends it up to the scroll. The keyboard still moves it, which is the
point of keeping focus reachable — arrows on a focused slider are a deliberate
gesture in a way the wheel over an unfocused one is not.

The readout is not here. `mockup/paper_primitives.py` argues that a slider's
value goes above the track and never beside it, since beside means the track
moves as the number's width changes — and that is an argument about the *row*, so
it is answered where a row is built. What the argument leaves this file is the
size policy: a slider takes the width it is given and nothing is placed to its
right, so a caller obeying it does not have to fight one that wanted to be 230px
wide the way the mockup's was.

Focus wears what hover wears, and gains no border. Everywhere else in this tree
focus takes `ACCENT` on an edge (`button.py`) or a ring outside it (`field.py`);
a slider's handle is already accent-filled, so the accent has nothing to say on
it, and a stylesheet border on a sub-control is added *outside* its stated width
— which would grow the handle on focus and shift the groove margin under it, the
reflow `field.py` refuses on a text field. So the handle takes the ink instead,
the same mark the pointer makes. That the two states look alike is not a
collision: both say *this is the one that moves next*, and a slider cannot be
hovered and keyboard-driven by two people at once. A slider standing in a `Field`
gets the ring around the whole control on top of this, and that is the wrapper's.

Only horizontal, and the orientation is not a parameter. Every sub-control rule
below is written `:horizontal` and a vertical slider would come out undressed
rather than wrong-looking, which is the failure that takes longest to see; the
first view that genuinely wants a vertical one can widen this deliberately.

`metrics.CHANGED` is not connected, unlike every other file in here. There is no
text in a slider and no radius of the card's — the two numbers below are the
groove and the handle, and neither is a size a user sets. A rebuild on every
type change would be a redraw for a signal this widget has no stake in.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy, QSlider, QWidget

from sieve.gui import palette
from sieve.gui.palette import ACCENT, LINE, TEXT, rgb

#: The slider's parts. The groove is a hairline in `LINE` because it is a track
#: and not a control; the part behind the handle is the accent, so the answer to
#: *how far along is this* is readable without finding the handle first. The
#: handle is four times the groove — enough to be a grab target at the pointer
#: sizes Qt reports, and the margin below is what re-centres it once it is.
_GROOVE = 3
_HANDLE = 12


class Slider(QSlider):
    """A horizontal slider in the tree's roles, that lets the wheel past it.

    It knows what it looks like and what it is at, and nothing about what its
    value means — `valueChanged` is the caller's, the same split every primitive
    here makes.
    """

    def __init__(self, low: int = 0, high: int = 100, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setObjectName("slider")
        self.setRange(low, high)
        # One per arrow and one per page, which are the same step: the ranges
        # these are used over are small enough that a click on the groove lands
        # on the value it was aimed at.
        self.setSingleStep(1)
        self.setPageStep(1)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # Takes the width it is given and asks for no height beyond its own —
        # see the module docstring on why nothing is placed to its right.
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._dress()
        # A bound method and never a lambda, for the reason `button.py` gives:
        # PySide6 drops a connection to a bound method when the receiver goes,
        # where a lambda closing over `self` keeps a dead slider subscribed.
        palette.CHANGED.connect(self._dress)

    def show_value(self, value: int) -> None:
        """Put the handle where the setting is, without saying it moved.

        The move a *reader* makes rather than a user: a row refreshing itself
        from what is stored is not a gesture, and a `valueChanged` out of it
        would be indistinguishable from a drag at the far end of whatever the
        caller connected. `setValue` to the value already held emits nothing on
        its own, so this matters only when the two have genuinely diverged —
        which is exactly the case a refresh exists for.
        """
        self.blockSignals(True)
        self.setValue(value)
        self.blockSignals(False)

    def wheelEvent(self, event) -> None:
        """Ignored, so it reaches whatever this is scrolling inside — see the
        module docstring."""
        event.ignore()

    def _dress(self) -> None:
        """The sheet, in the palette now in use.

        Scoped to `#slider` rather than to `QSlider`, for the reason
        `sections.py` gives: this stands inside a card whose sheet is set on an
        ancestor, and a bare class rule would reach every slider in the pane.
        That scoping is the half of this lift the preferences section could not
        do for itself — its sheet addressed `QSlider` by class and was safe only
        while it held no slider it had not made, which is a promise a section
        cannot keep for the views that come after it.
        """
        self.setStyleSheet(f"""
            #slider::groove:horizontal {{
                background: {rgb(LINE)};
                height: {_GROOVE}px;
                border-radius: {_GROOVE // 2}px;
            }}
            #slider::sub-page:horizontal {{
                background: {rgb(ACCENT)};
                height: {_GROOVE}px;
                border-radius: {_GROOVE // 2}px;
            }}
            #slider::handle:horizontal {{
                background: {rgb(ACCENT)};
                width: {_HANDLE}px;
                border-radius: {_HANDLE // 2}px;
                margin: -{(_HANDLE - _GROOVE) // 2}px 0;
            }}
            #slider::handle:horizontal:hover {{ background: {rgb(TEXT)}; }}
            #slider::handle:horizontal:focus {{ background: {rgb(TEXT)}; }}
            #slider::sub-page:horizontal:disabled {{ background: {rgb(LINE)}; }}
            #slider::handle:horizontal:disabled {{ background: {rgb(LINE)}; }}
        """)
