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

`slider.py` is the third control and is the first thing here that arrived the
ordinary way rather than ahead of a view: preferences had built one, the mockup
had settled the same shape, and the tuning pane this project is for wants a third
— which is the same *two views turned out to be drawing this* that lifted the
card and the sections, and not the budget argument the two controls above it were
settled on.

`check.py` is the fourth control and arrived the way the first two did rather
than the way the slider did: what a *set* state looks like is a mark spent
everywhere — a write list, a choice of estimator, a row of options in a box — and
the first view to draw a ticked box would be fixing it for every view after.
Emphasis is the buttons' budget and focus is the field's; this is the third of
the same kind, and it is why the three of them are settled before there are three
views to argue over them.

Settling it is also what turned two constants public. A checkbox is editable, so
its resting edge is the step `field.py` argues for; it is filled, so it answers
the pointer by the step `button.py` argues for; and it paints its own focus ring,
having no wrapper to paint one for it. Each is imported from the file that makes
the case rather than restated — a second 0.14 written here would be a second
answer to *what does the pointer do*, free to drift from the first.

`select.py` is the fifth control and arrives the way the first two did. It is
the third answer to *pick one* — the radio is a fixed few all visible, the
section list is a few that move you, this is many — and what it settles is not
the box but the list that drops out of it: the first dropdown, the first
completer and the first inline menu are one decision, and the tree already made
it for the window's menus in `frame/chrome.py`. Taking that dress rather than
the mockup's accent wash is what keeps a dropped select and a dropped menu one
object instead of two.

Settling it turned a third constant public, for a reason the other two do not
have. `field.RADIUS` is not a corner a control chooses; it is the corner
`Field` draws its focus ring at, so a styled control meant to stand inside one
takes that number or gets a ring that no longer follows its box.

`view.py` is the fourth shape and is under the other two rather than beside them:
the head a pane wears was the stack's band until a view that is not a column of
cards wanted the same line at its top, and it moved here so that a head is one
decision rather than one per pane. Everything a view stands in starts as one of
these.
"""

from __future__ import annotations

from sieve.gui.primitives.button import DEFAULT, GHOST, PRIMARY, SUBTLE, Button
from sieve.gui.primitives.card import Card
from sieve.gui.primitives.check import Check
from sieve.gui.primitives.field import Field, LineField
from sieve.gui.primitives.nav import SectionNav
from sieve.gui.primitives.sections import Section, SectionCard
from sieve.gui.primitives.select import Select
from sieve.gui.primitives.slider import Slider
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
    "Check",
    "Field",
    "LineField",
    "Section",
    "SectionCard",
    "SectionNav",
    "Select",
    "Slider",
    "View",
]
