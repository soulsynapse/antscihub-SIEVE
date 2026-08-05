"""The full-width band: where a frame lands on the strip, and what a click means.

Two modules, one painting and one arithmetic, split for `gui/chain_model.py`'s
reason: every rule in `geometry.py` is wrong at the first or the last frame
before it is right anywhere, and a rule written inline in a `paintEvent` is one
whose failure is a band a few pixels off rather than a red test.

The band reads the transport and the document; neither reads it. That
one-directional edge is why `transport` names this package in its forbidden
list — `player` needing a column position would be the timeline drawing itself
from below.
"""
