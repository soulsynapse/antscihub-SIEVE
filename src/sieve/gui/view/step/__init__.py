"""The step: the one in the chain the user is standing on, and its knobs.

The third position on the right pane's track (`frame/swipe.py`) — the step you
walked into, after the chain it is in. It is the chassis so far: a head, and a
room saying there is no step open. What a step's surface holds is not built here
yet, and nothing in this folder names the position or the pane it stands in
(ADR-0001).
"""

from __future__ import annotations

from sieve.gui.view.step.view import Step

__all__ = ["Step"]
