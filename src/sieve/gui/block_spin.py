"""The Block spin box: a size, a mode below it, and no refusal between them.

Block size is entered as a block *edge in working pixels*, so scrolling it
**down** multiplies the block count: one wheel notch from a comfortable value
takes B from a few hundred toward the crop's whole pixel count. Everything
downstream of the count is linear in it.

**This control used to refuse the small end.** `density_plot.MAX_BLOCKS` was
the largest B the density surface would bin and `block_signal.min_block_for`
turned it into a per-replicate floor, so a range of sizes did not exist and the
spin box stepped over them. That is gone (2026-07-28,
`docs/todo/budgets-attribute-cost-they-do-not-cap-it.md`): block count is a
scientific choice about the grain of the analysis, and the ceiling that
justified the refusal was one workstation's timing. The stall it was protecting
against is gone too — the binning left the GUI thread — so what a large B now
costs is time, which the HUD attributes, rather than a frozen window.

What remains is one boundary, and it is semantic rather than performance:
`0 = auto` is a *mode*, not a smaller size. A crank down the range stops at 1
before it reaches auto, so an accelerated run cannot cross into the mode
without the user seeing the smallest size on the way.
"""

from __future__ import annotations

from PySide6.QtWidgets import QSpinBox, QWidget

#: `0 = auto`: the block edge is fixed at 64 *source* pixels and the count
#: follows from the source rather than from this knob.
AUTO = 0


class BlockSpinBox(QSpinBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Interpret on commit, not per keystroke: with keyboard tracking on, a
        # partially typed "15" would be read as "1" and pushed to the chain.
        # `crop_tools.py` turns it off for the neighbouring reason — an edit
        # runs from the first keystroke to a commit and nothing in between
        # reaches the document.
        self.setKeyboardTracking(False)
        self.setToolTip("Block edge in working pixels; 0 is auto (64 source pixels).")

    def stepBy(self, steps: int) -> None:
        target = self.value() + steps
        if target <= AUTO and self.value() > 1:
            # However many notches the acceleration was worth, the run ends at
            # the smallest size; the next one after that reaches the mode.
            target = 1
        self.setValue(max(self.minimum(), min(self.maximum(), target)))
