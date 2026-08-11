"""Card mock ups: the shapes a card could take, drawn beside each other.

The card is the one primitive every pane will be full of — a chain is a column
of them, the library already is one — so what it looks like is the decision with
the widest blast radius in the interface, and the cheapest place to make it is
before there are twenty on screen.

Drawn rather than described. A card's real question is what a *column* of them
does to the eye: whether four icons on every row read as available or as noise,
whether a 3px edge is findable at a glance, whether a border is doing work a
gutter could do. None of that survives being written down, and all of it is
answered by looking at the alternatives at the size they will be seen.

Two files, for `view/__init__.py`'s reason: `look.py` is the candidates and the
widget that draws one, `view.py` is how a pair of them is laid out. A look is
added by appending to `LOOKS` and neither is opened. The scrolling column both
sit in is the bench's own (`dev/gallery.py`), shared with the title mock ups.
"""

from __future__ import annotations

from sieve.gui.view.dev.card_mockups.view import CardMockups

__all__ = ["CardMockups"]
