"""The shapes a view is built out of, owned by none of them.

A primitive knows what it looks like and what gestures it offers, and nothing
about what taking one of them means: the card here paints a panel and emits
`removed`, and whether that drops a step from a chain or a row from a library is
the view's to answer. Held beside `palette.py` and above `view/` for the same
reason the palette is — a card that lived in `view/chain/` would be imported
back up out of it by the next view that wanted one.

`sections.py` and the `nav.py` under it are the second shape and arrived the
same way: preferences drew a list of sections against one of them open, the dev
view turned out to be that picture again, and the shape moved up here rather
than the second view importing the middle of the first.
"""

from __future__ import annotations

from sieve.gui.primitives.card import Card
from sieve.gui.primitives.nav import SectionNav
from sieve.gui.primitives.sections import Section, SectionCard

__all__ = ["Card", "Section", "SectionCard", "SectionNav"]
