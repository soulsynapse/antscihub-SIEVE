"""The library: every project remembered, and which one the work is standing in.

The first view, and the first position on the right pane's swipe (`swipe.py`) —
the project you opened, before the chain in it. It lists and never mints: there
is no project document yet for a NEW PROJECT to write, and a button that opened
a file picker and appended a row would be the library, invented in a view.

What the list is handed is `Project`, which is a card's worth of already-written
lines and not a document — where the real ones come from is still open.
"""

from __future__ import annotations

from sieve.gui.view.project_list.card import ProjectCard
from sieve.gui.view.project_list.project import Project
from sieve.gui.view.project_list.view import ProjectList

__all__ = ["Project", "ProjectCard", "ProjectList"]
