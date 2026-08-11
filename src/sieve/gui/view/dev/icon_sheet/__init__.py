"""Icons: every vendored lucide glyph, in each ink a widget draws it in.

The set is small and the reason to draw it is not that there is a lot of it. An
icon in this tree is a pixmap and not text, so every state a stylesheet used to
handle — hover, disabled, the pinned card's filled ◆ — is now a separate
drawing made at the colour in force when it was made (`gui/icons`). That is four
drawings per glyph that no rule can correct after the fact, and the only way to
know a shape survives all four is to see all four beside each other. The palette
is chosen a section away on the same card, which is the other half: a glyph that
reads on slate and disappears on the light palette is a fault this section is
where you find.

Two files, for `card_mockups`' reason: `sheet.py` is what there is and what each
glyph is for, `view.py` is the table it is drawn as. A glyph is vendored by
dropping the SVG in `gui/icons/lucide/` — it appears here with no file in this
folder being opened, under `not spoken for yet` until `sheet.py` says what it is
for.
"""

from __future__ import annotations

from sieve.gui.view.dev.icon_sheet.view import IconSheet

__all__ = ["IconSheet"]
