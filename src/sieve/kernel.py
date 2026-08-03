"""The kernel: the five-shape op algebra, vocabulary v1, one design unit.

Shape is classification (ARCHITECTURE.md invariant 3). The settled table
(ARCHITECTURE.md "The components"; DESIGN-SESSION.md Exchanges 3 and 5):

    Resample  coordinate map over (t, y, x)
    PixelMap  value -> value
    Window    frame N from [N-a, N+b]
    Fold      (state, frame) -> (state, output)
    Opaque    frames in, frames out -- always correct, never fused

Closed means growth is deliberate additive revision at the framework
level, never a per-tool extension point; Opaque is the total escape
hatch, so no op is ever inexpressible, only slow. How a second input
enters these signatures is unpinned and recorded in DEFERRED.md.
"""

from sieve.debt import Owed

raise Owed(
    "20260802T023505Z: five-shape op algebra as one unit (Resample, PixelMap, Window, Fold,"
    " Opaque), vocabulary v1 under additive revision; ARCHITECTURE.md 'The"
    " components', DESIGN-SESSION.md Exchanges 3 and 5"
)
