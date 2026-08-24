"""The playhead, and eventually the strip under it.

Standing here as the smallest thing that plays: a clock, a loop over a row
range, and a request per frame. What it looks like is provisional and meant to
be replaced by a designed strip; what is not provisional is the arrangement —
the transport owns a clock and asks, the window answers — and the rule that the
playhead follows the clock while the drawing follows the machine.
"""

from __future__ import annotations

from sieve.gui.view.transport.view import Transport

__all__ = ["Transport"]
