"""One project as the list reads it: a name and three lines already written.

`holds` and `opened` are sentences and not counts and timestamps, because the
library that will supply them does not exist yet and a view that turned `6` into
"6 sources" would be the place a decision about what a source is had been
recorded. Handing the view the finished line keeps that decision where the
library will make it, and leaves this file able to say what a card shows without
claiming anything about what a project *is*.

Frozen for the same reason: the list redraws from what it was handed, so an
entry the view could edit in place would be a second copy of the library that
nothing writes back.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    """A row in the library: what it is called, what it holds, where it lives."""

    #: The name on the card. A file's name, not an identifier — two projects may
    #: share one, and nothing in the list is keyed by it.
    name: str

    #: What is in it, in the user's terms — "6 sources · 6000 frames @ 30 fps".
    holds: str

    #: When it was last opened, written as it is to be read — "3 days ago".
    opened: str

    #: The folder the project file sits in. Held so the card can offer to show
    #: it on disk, and because a name alone cannot say which of two is which.
    folder: str
