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

`segmented.py` is the sixth control and closes the set of *pick one*: the radio
is a fixed few each readable alone, the section list is a few that move you, the
select is many that will not stand open, and this is the few whose options only
mean anything against each other. Four controls rather than one that stretches,
because the question a view actually has is how many and how they are read, and
there is an answer at each size.

Settling it turned a fourth constant public, and the reason is the one the other
three have. `nav.MARK_W` is not a nav's look; it is how wide the mark that says
*this is the current one* is drawn, and a bar wearing that mark along its foot
rather than down its side is the same decision seen on the other axis. What the
bar does *not* borrow is the accent wash the mockup lights its current segment
with — the tree's answer to which of a visible few is current is already the
nav's edge, and a wash would be both a ninth role and a second answer.

`view.py` is the fourth shape and is under the other two rather than beside them:
the head a pane wears was the stack's band until a view that is not a column of
cards wanted the same line at its top, and it moved here so that a head is one
decision rather than one per pane. Everything a view stands in starts as one of
these.

`pill.py` is the first thing here that is neither: a surface is what the work is
seen in and a control is what it is done with, and this is a mark the interface
*makes* about something and takes no gesture for. It arrives the way the budget
controls did — ahead of a view asking — because what a state looks like is spent
everywhere, and the first view to draw a running step would be fixing it for all
of them.

Settling it turned no constant public and refused a role instead, which is the
same answer `button.py` gave danger and is worth having given twice. The mockup
lights its three states green, amber and grey; two of those are hues past the
one every palette commits to, so the dot takes the accent, the ink and `DIM`,
and the word — which the mockup already says is what carries the meaning — does
the rest. What that costs is a fourth state, failure, which cannot be told from
*off* without the hue and so is not offered here at all.

`banner.py` is the second mark and is where that cost was paid. A pill is the
size of a word and can say what state a thing is in; it cannot say why, and a
failed run, a missing input and two files written are three things every view in
this tree can end up having to report. So the refusal is made once more and
answered rather than deferred: the mockup's four kinds are told apart by a
painted *shape* — a dot, a tick, a cross, a triangle — and the only colour spent
is the one question the tree can ask, which is whether the thing wants the user
now. That is the accent for a warning and a failure and `DIM` for a note and a
report, so four kinds cost no role at all.

It is also the first thing here besides the card to follow `metrics.radius()`
rather than decline it. Every control declines on the grounds that the slider is
*card corners*; a banner is a full-width block with a title on a ground, which
is a card in everything but the verbs, and one that kept its own corner would be
the one shape in a stack not moving when the stack did.

`table.py` is the fifth surface and the first thing here that holds *data*. The
others are handed whatever a view builds and know nothing about it; this is
handed rows, and a row is a fact about something the user did not draw. It
arrives ahead of a view for the reason `check.py` names while settling on it —
the write list, a run's steps against their costs, and a sheet of detections are
one picture drawn three times, and the first to invent a header, a rule and a
current row would be fixing all three.

Settling it turned no constant public and spent one instead. `nav.MARK_W` was
made public by `segmented.py`, which wears the mark along a bar's foot rather
than down a row's side; a table's rows wear it exactly where the nav's entries
do, which is what makes *this is the current one* one drawing in this tree
rather than a family of them. What it refuses is the mockup's accent wash under
the selected row, on `segmented.py`'s grounds, and the mockup's mono numerals,
on `field.py`'s — a family is the tree's first and belongs in `metrics.py` when
it is chosen, and right-alignment is the half of that treatment that costs no
decision.

`menu.py` is the sixth surface and the only thing here that arrived because the
tree was already paying for not having it. Every other file was lifted ahead of
a view or when a second view turned out to be drawing the same picture; this one
is a decision that had *two* copies before it had a home — `frame/chrome.py`
answered what a list appearing over the work looks like, `select.py` took that
answer deliberately and then wrote the rules out again, and the comment naming
which was the original is what a drift starts as. So the dress moves here and
chrome takes it from this file, which leaves the window's chrome dressing the
window rather than also being the tree's only copy of a shape any card can open.
`select.py` still restates it, and that one is not duplication that can be
removed: a combo's popup is a `QAbstractItemView` and a menu is a `QMenu`, and
no selector reaches both.

Settling it turned no constant public and declined three things. The danger red
goes on `button.py`'s grounds, for the third time after `pill.py` and
`banner.py` — what the mockup paints red is a destructive verb, and the word is
what carries that here. The accent wash under the highlighted row goes on the
grounds that were the point of moving the file at all: a dropped select and a
dropped menu are one object on one screen, and that object's highlight is
`PANEL_HOT`. The corner goes for a reason none of the others have — a menu is a
top-level popup, and a rounded one needs a translucent background whose corners
a compositor rather than Qt has to answer.

What it keeps from the mockup, and chrome does not have, is the captioned group
and the shortcut column: the two things that make a menu of fifteen verbs
readable rather than a wall. Neither is Qt's own drawing. The caption is a
disabled row holding a label rather than `addSection`, whose look is the
platform's — the same reason `segmented.py` is not a `QTabBar` — and the column
is only the room reserved for a shortcut Qt already draws right-aligned.

`meter.py` is the third mark and arrived for `menu.py`'s reason rather than for
the other two marks': a pill says what state a thing is in and a banner says what
happened to it, and this is the one that is a number — but what moved it here is
that the tree was already paying. `card.py` held the only copy, four pixels
across a card's foot with its own height and its own rule for the accent, and
`table.py` landed with cells that take a widget beside a numeric column, which is
the mockup's `Cellbar` and the second place the same bar is wanted. So the
drawing moves here and the card takes it from this file, which leaves the card
deciding whether it has a foot rather than also being the tree's only answer to
what a length looks like.

Settling it turned `card.py`'s meter height public and paid the hue refusal a
fourth time, at a cost the earlier three did not have. The mockup lights the bar
amber past the step's share of the frame budget; the accent is the only hue and
already means *the one you are acting on*, so the two questions collapse and what
the tree keeps is selection — which is what the card was already doing with it. A
meter therefore cannot say *this is expensive*. The number at the other end of
the row says it instead, which is what the mockup's own card draws beside the
bar, and it says it in milliseconds rather than in a threshold somebody picked.

The one thing it declines that no other file here has had to is the type slider.
Every mark and control above either follows a text role or fixes a drawing at a
pixel size; this fixes both its thickness and its length, because a mark whose
meaning *is* its size cannot also take that size from a preference — two bars in
one column at two sizes would not be comparable, and comparison is the whole of
what the shape is for.
"""

from __future__ import annotations

from sieve.gui.primitives.banner import DONE, FAIL, NOTE, WARN, Banner
from sieve.gui.primitives.button import DEFAULT, GHOST, PRIMARY, SUBTLE, Button
from sieve.gui.primitives.card import Card
from sieve.gui.primitives.check import Check
from sieve.gui.primitives.field import Field, LineField
from sieve.gui.primitives.menu import Menu
from sieve.gui.primitives.meter import Meter
from sieve.gui.primitives.nav import SectionNav
from sieve.gui.primitives.pill import IDLE, LIVE, OFF, Pill
from sieve.gui.primitives.sections import Section, SectionCard
from sieve.gui.primitives.segmented import Segmented
from sieve.gui.primitives.select import Select
from sieve.gui.primitives.slider import Slider
from sieve.gui.primitives.stack import CardStack
from sieve.gui.primitives.table import Column, Table
from sieve.gui.primitives.view import View

__all__ = [
    "DEFAULT",
    "DONE",
    "FAIL",
    "GHOST",
    "IDLE",
    "LIVE",
    "NOTE",
    "OFF",
    "PRIMARY",
    "SUBTLE",
    "WARN",
    "Banner",
    "Button",
    "Card",
    "CardStack",
    "Check",
    "Column",
    "Field",
    "LineField",
    "Menu",
    "Meter",
    "Pill",
    "Section",
    "SectionCard",
    "SectionNav",
    "Segmented",
    "Select",
    "Slider",
    "Table",
    "View",
]
