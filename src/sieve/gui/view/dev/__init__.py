"""The dev view: the application looked at by whoever is building it.

The second view the frame stands on an overlay, and it is there for preferences'
reason read one step further: preferences are about the application rather than
about the project, and this is about the *build* rather than about either. It is
read instead of the work, never beside it, so it takes no pane — and it is not a
position on the swipe, because it is not a step in anything the user does.

It is the same card as preferences and says so by being one (`primitives/
sections.py`). What differs is that a dev section usually has something under
it: preferences names places settings will land, and a bench that named places
and showed nothing would be a menu of tools that do not exist.

One folder per section, for `view/__init__.py`'s reason one level down: a
section arrives as a surface and not a widget, and the gallery under `card
mock ups` is worth reading on its own without the bench's own file having to
carry it. `view.py` here holds only what every section shares — which sections
there are, in what order, and what each is for.

Nothing in the application reads this. It is a window onto the tree for whoever
is editing it, which is why it may draw shapes the product has not chosen: a
mockup that had to be a supported look would be an implementation and not a
mockup.
"""

from __future__ import annotations

from sieve.gui.view.dev.view import Dev

__all__ = ["Dev"]
