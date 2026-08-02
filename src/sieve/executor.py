"""The executor: the only component that knows the others (ARCHITECTURE.md).

Only render is placed: crop is Resample-shaped end to end, so the
milestone reaches no sequential evaluation. sweep(node, range), fusion
and the peephole rules, and the instrumentation/cost surface are
not-yet-due intentions with their triggers in DEFERRED.md.
"""

from sieve.debt import Owed


def render(node, frame):
    raise Owed(
        "render(node, frame): pull-based single-frame evaluation, including"
        " the LRU frame cache the pull path requires to feel correct;"
        " ARCHITECTURE.md 'The executor', DESIGN-SESSION.md Exchange 4"
    )
