"""The Block spin box, and the sizes it will not accept.

Block size is entered as a block *edge in working pixels*, so scrolling it
**down** multiplies the block count: one wheel notch from a comfortable value
takes B from a few hundred toward the crop's whole pixel count. Everything
downstream of the count is linear in it, and one thing downstream of it runs on
the GUI thread — `DensityPlot.set_series` bins the entire `(T, B)` band power
per rebuild. At B in the hundreds of thousands that was measured in seconds
(`docs/findings/2026.07.27-the-density-histogram-was-a-scatter.md`), which is a
frozen window, and a frozen window is a control that looks more live than it is.

**So the control refuses rather than the surface computes slowly** (rule 6).
The refused range is a *hole*, not a floor, because `0 = auto` sits below it and
must stay reachable: auto is fixed at 64 *source* pixels, so its block count is
a property of the source rather than of the knob, and it is under the bound for
any source below roughly 8192x8192. Sizes from 1 up to the derived floor are the
ones that do not exist; the spin box steps over them in both directions and
snaps a typed one to the nearest legal value.

**The floor is derived, not chosen.** `density_plot.MAX_BLOCKS` is the largest B
`tests/bench/test_density_rebuild.py` pins against the `density_rebuild` budget,
and `block_signal.min_block_for` reads it back through the same ceiling division
the kernel's grid uses. The floor therefore moves with the replicate's crop
extent — the same block size is legal on a small crop and refused on a large one
— which is why `set_floor` is called from the tab whenever the extent or the
rescale factor moves, rather than once at construction.

*Rejected:* letting every legal value compute and leaving the benchmark to guard
the cost. The benchmark runs in CI against the reference count, never against
the value a wheel notch just set, so it cannot protect the session that matters.
"""

from __future__ import annotations

from PySide6.QtWidgets import QSpinBox, QWidget

#: `0 = auto`, and it is always legal — see the module docstring.
AUTO = 0


class BlockSpinBox(QSpinBox):
    """A spin box over `{0} | [floor, max]`, with `(0, floor)` refused.

    Wire and read it exactly like a `QSpinBox`; the hole is enforced on the
    three paths a value can enter through — the wheel and the arrows
    (`stepBy`), and typing (`valueFromText`, at commit).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._floor = 1
        # Interpret on commit, not per keystroke: with keyboard tracking on,
        # snapping "1" up to the floor would rewrite the line edit before "15"
        # could be finished being typed. `crop_tools.py` turns it off for the
        # neighbouring reason — an edit runs from the first keystroke to a
        # commit and nothing in between reaches the document.
        self.setKeyboardTracking(False)

    @property
    def floor(self) -> int:
        """The smallest legal explicit block size. `AUTO` is legal below it."""
        return self._floor

    def set_floor(self, floor: int, *, reason: str = "") -> None:
        """Refuse explicit sizes under `floor`, and say so in the tooltip.

        **A value already below the new floor is left exactly where it is.**
        The floor governs what may be *entered*; it is not a claim about what
        the pipeline currently holds. A project saved before this bound
        existed, or one whose crop grew under a fixed block size, is a real
        parameter value, and a widget that silently raised it would show a
        number the chain does not hold — the mirror of rule 6, a control
        looking more settled than it is. The stall such a value causes is
        refused at the surface instead (`density_plot.set_series`), which is
        the one place every path into the value passes through.
        """
        self._floor = max(1, floor)
        self.setToolTip(
            f"Block edge in working pixels; 0 is auto.\n"
            f"Sizes below {self._floor} are refused here" + (f" — {reason}." if reason else ".")
        )

    def stepBy(self, steps: int) -> None:
        """Step over the hole: up lands on the floor, down stops at it first.

        Downward is deliberately two steps rather than one. Auto is a *mode*
        and the floor is the smallest *size*, so a crank down the range stops
        at the size before it reaches the mode — otherwise an accelerated run
        would cross a semantic boundary without the user seeing the value they
        were heading for.
        """
        target = self.value() + steps
        if AUTO < target < self._floor:
            target = self._floor if steps > 0 or self.value() > self._floor else AUTO
        self.setValue(max(self.minimum(), min(self.maximum(), target)))

    def valueFromText(self, text: str) -> int:
        """A typed size inside the hole commits as the floor, not as itself."""
        value = super().valueFromText(text)
        return self._floor if AUTO < value < self._floor else value
