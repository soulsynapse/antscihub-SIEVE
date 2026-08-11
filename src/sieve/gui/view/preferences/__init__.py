"""Preferences: what the application is set to, as against what a project holds.

The first view the frame does not house in a pane — it stands on an overlay over
all three (`overlay.py`), because it is read instead of the work rather than
beside it. That is the frame's decision and not this view's: nothing here names
an overlay any more than the project list names a pane, and standing this in a
pane instead would be an edit in the window and nothing else.
"""

from __future__ import annotations

from sieve.gui.view.preferences.view import Preferences

__all__ = ["Preferences"]
