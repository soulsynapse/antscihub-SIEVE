"""The library: every project remembered, and which one the work is standing in.

The first view, and the first position on the right pane's swipe (`swipe.py`) —
the project you opened, before the chain in it. It lists and never mints, and
that is still true now that it carries a plus: the button emits `add_requested`
and the window answers it, the same shape as `opened`. What the earlier version
of this file refused was a button that *was* the library — one that opened a
picker and appended a row of its own — and it refused it because there was no
library for the verb to belong to. There is one now (`sieve.project`), the
window owns it, and asking is not minting.

What the list is handed is `Project`, which is a card's worth of already-written
lines and not a document: the rows are built where projects are understood, so
that what a project *holds* is not a decision this view made by formatting one.
"""

from __future__ import annotations

from sieve.gui.view.project_list.card import ProjectCard
from sieve.gui.view.project_list.project import Project
from sieve.gui.view.project_list.view import ProjectList

__all__ = ["Project", "ProjectCard", "ProjectList"]
