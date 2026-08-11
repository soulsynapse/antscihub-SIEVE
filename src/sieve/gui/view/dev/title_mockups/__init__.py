"""Title mock ups: the shapes a pane's head could take, drawn beside each other.

Every pane gets one — `projects` over the library, the project's name over the
pipeline — and there is no primitive behind any of them: the library builds its
head inline (`project_list/view.py`), and the next pane that wants one will
either copy that row or invent a second. Both of those are how a screen ends up
with two heads that differ by things nobody chose, and the cheapest moment to
settle it is while there is exactly one.

Drawn rather than described, for the card gallery's reason read one level up. A
head's real question is what it does to the pane under it — whether the eye can
tell where the chrome stops without a rule, what a row of chrome costs on a
screen whose point is the footage, how much width is left for a name the user
typed in the fourth month. None of that survives being written down.

Two files, matching `card_mockups/`: `look.py` is the candidates and the widget
that draws one, `view.py` is how a pair is laid out over a stub of a pane. A
look is added by appending to `LOOKS`. The scrolling column both galleries sit
in is the bench's own (`dev/gallery.py`).
"""

from __future__ import annotations

from sieve.gui.view.dev.title_mockups.view import TitleMockups

__all__ = ["TitleMockups"]
