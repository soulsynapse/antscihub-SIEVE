"""The view vocabulary: the closed language between tools and the GUI.

Vocabulary v1 -- image, mask, points, paths, vectors, regions, series
strip (DESIGN-SESSION.md Exchange 5, "The view vocabulary is closed").
Closed means additions are deliberate framework-level revisions the
renderer learns once and every tool then speaks, never per-tool
extension points. Owned by neither side: tools declare in it, the GUI
interprets it -- the same seam the op shapes hold outside the executor.
"""

from sieve.debt import Owed

raise Owed(
    "20260802T023511Z: closed view vocabulary v1 (image, mask, points, paths, vectors,"
    " regions, series strip) under additive revision; ARCHITECTURE.md 'The"
    " GUI', DESIGN-SESSION.md Exchange 5"
)
