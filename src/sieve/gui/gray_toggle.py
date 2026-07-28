"""The viewport's gray toggle: the affordance lives where the symptom is.

A preferences checkbox is where a setting goes to be found by someone who
already knows it exists. The person who needs this is watching a stuttering
pane *right now* and does not know that colour is what they are paying for —
so the control sits in the filter tab's top-right corner, over the tuning
surface where the stutter is felt, beside the playback-speed cycler. Both
its states name the format and the multiplier ("Color · 1x", "Gray · ~2.5x"):
a label that said just "grayscale" would read as a viewing preference, which
is the one thing this is not — nobody wants gray, they want the frame rate.

Two behaviours share the one button, and the button is the announcement for
both (rule 6's mirror clause — the state is shown by the same affordance that
can override it, not by a separate badge):

**Manual.** Clicking outside a render toggles the persisted preference
(`Preferences.viewport_luma`). Off by default — a grayscale pane is a
surprise to everyone who did not ask for it, and the analytical cost of
colour is zero; the graphs are computed from luma either way.

**Automatic, while a render is filling.** The window render and the player
contend for decode bandwidth, and luma is the only configuration above real
time while a render runs (2026-07-27 finding: 52.3 fps against colour's
19.6). So the pane drops to gray on its own while a window render fills and
returns to colour when it finishes; the button shows it engaged with the
reason in its label. Clicking it during a render pins colour and the
automatic behaviour stands down until the render (or burst of renders — the
pin outlives a resubmission, not the episode) is over. The pre-stated
falsifier: if the pane changing appearance unbidden reads as a fault in
practice, drop the automatic half; the manual toggle is unchanged either way.

The effective format — what the player is actually told — is
`manual or (rendering and not pinned)`, and `luma_changed` carries every
change of that answer. This widget owns the policy so the player can stay a
transport and the window can stay wiring.
"""

from __future__ import annotations

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QToolButton, QWidget

from sieve.gui.preferences import Preferences

#: Both states name the format and its playback multiplier, so the button
#: reads as the tradeoff it is rather than a viewing preference. "~2.5x" is
#: the measured ratio on the reference workload during a render (52.3 fps
#: against 19.6); alone it is closer to 2.3x (100.8 against 43.1).
LABEL_COLOR = "Color · 1x"
LABEL_GRAY = "Gray · ~2.5x"
#: Why the pane went gray by itself, stated by the same control that undoes it.
LABEL_AUTO = "Gray · ~2.5x · rendering"

_TOOLTIP = (
    "Decode the viewport in grayscale: colour off, playback roughly 2.5x.\n"
    "The graphs are computed from luma either way — this changes nothing "
    "about the analysis.\nWhile a render is filling the pane goes gray on "
    "its own; clicking then keeps colour for that render."
)


class GrayToggle(QToolButton):
    """The one control over the viewport's decode format."""

    #: The effective format changed. Carries what the player should decode.
    luma_changed = Signal(bool)

    def __init__(self, preferences: Preferences, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._preferences = preferences
        self._manual = preferences.viewport_luma
        self._rendering = False
        self._pinned = False
        self._effective = self._manual

        self.setCheckable(True)
        self.setToolTip(_TOOLTIP)
        self.clicked.connect(self._on_clicked)
        # `restore_defaults`, or a second surface some day: the store is the
        # one home of the manual answer, so follow it rather than fork it.
        preferences.changed.connect(self._on_preferences_changed)
        self._refresh()

    @property
    def effective_luma(self) -> bool:
        """What the viewport should decode right now."""
        return self._effective

    @Slot(bool)
    def set_rendering(self, active: bool) -> None:
        """A window render started filling, or stopped. The auto half's input."""
        if active == self._rendering:
            return
        self._rendering = active
        if not active:
            # The pin was "for that render", and the render is over.
            self._pinned = False
        self._refresh()

    @Slot()
    def _on_clicked(self) -> None:
        """Gray if colour, colour if gray — whatever made it gray.

        A click on an auto-engaged button means "I want colour", so it pins
        as well as clearing any manual state; a manual toggle that merely
        fell back to auto-gray would be a click that visibly did nothing.
        """
        if self._effective:
            if self._manual:
                self._manual = False
                self._preferences.viewport_luma = False
            if self._rendering:
                self._pinned = True
        else:
            self._manual = True
            self._pinned = False
            self._preferences.viewport_luma = True
        self._refresh()

    @Slot()
    def _on_preferences_changed(self) -> None:
        stored = self._preferences.viewport_luma
        if stored == self._manual:
            return
        self._manual = stored
        self._refresh()

    def _refresh(self) -> None:
        effective = self._manual or (self._rendering and not self._pinned)
        auto = effective and not self._manual
        self.setChecked(effective)
        if not effective:
            self.setText(LABEL_COLOR)
        else:
            self.setText(LABEL_AUTO if auto else LABEL_GRAY)
        if effective != self._effective:
            self._effective = effective
            self.luma_changed.emit(effective)
