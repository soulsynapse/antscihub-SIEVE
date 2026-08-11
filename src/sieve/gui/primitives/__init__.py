"""The shapes a view is built out of, owned by none of them.

A primitive knows what it looks like and what gestures it offers, and nothing
about what taking one of them means: the card here paints a panel and emits
`removed`, and whether that drops a step from a chain or a row from a library is
the view's to answer. Held beside `palette.py` and above `view/` for the same
reason the palette is — a card that lived in `view/chain/` would be imported
back up out of it by the next view that wanted one.
"""

from __future__ import annotations

from sieve.gui.primitives.card import Card

__all__ = ["Card"]
