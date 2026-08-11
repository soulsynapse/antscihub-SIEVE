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

`card.py` and `stack.py` are the two halves of one drawing and were settled
together in `mockup/paper_cards.py` — the card, and the header and ground it is
seen in. They are two files because a card is put in things other than a stack,
not because the decisions are separable: the card's fill and the stack's ground
are the same choice made once, and either moved alone stops being it.

`button.py` is the first thing here that is a *control* rather than a surface,
and it arrived from `mockup/paper_primitives.py` ahead of a view asking for one
— which is the opposite of how the shapes above it got here, and is deliberate.
A card or a section is a picture two views turned out to be drawing; emphasis is
a budget spent across the whole application, and the first view to grow a filled
button would be the one setting that budget for every view after it. Settling it
before there are three is what keeps *one filled button per screen* a rule
rather than a description of whichever screen was built first.

`field.py` is the second control and arrived the same way and for the same kind
of reason: focus is not a card's decision or a form's, it is where the keyboard
is pointing, and a tree with two answers to that has none. Held here rather than
in whichever view first wanted somewhere to type.

`view.py` is the third shape and is under the other two rather than beside them:
the head a pane wears was the stack's band until a view that is not a column of
cards wanted the same line at its top, and it moved here so that a head is one
decision rather than one per pane. Everything a view stands in starts as one of
these.
"""

from __future__ import annotations

from sieve.gui.primitives.button import DEFAULT, GHOST, PRIMARY, SUBTLE, Button
from sieve.gui.primitives.card import Card
from sieve.gui.primitives.field import Field, LineField
from sieve.gui.primitives.nav import SectionNav
from sieve.gui.primitives.sections import Section, SectionCard
from sieve.gui.primitives.stack import CardStack
from sieve.gui.primitives.view import View

__all__ = [
    "DEFAULT",
    "GHOST",
    "PRIMARY",
    "SUBTLE",
    "Button",
    "Card",
    "CardStack",
    "Field",
    "LineField",
    "Section",
    "SectionCard",
    "SectionNav",
    "View",
]
