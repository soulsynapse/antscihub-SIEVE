"""The running session: what is being served, filled, computed and recorded.

`ledger` is the record — what the session spent, what it wasted, and what it
cannot yet account for (ADR-0008). The rest of this package arrives with the
phases that need it: the fill frontier and the proxy builder, the ladder that
chooses a tier, and the session object that owns the source, the stores and the
crop.

The one rule that belongs to this layer and can be stated before the rest of it
exists: a miss decode never runs on the GUI thread, and the GUI thread blocks
only for an exact request the user just released. Everything else serves a
cheaper answer and lets the fill overtake it
(`docs/findings/2026.08.22-what-froze-the-felt-loop.md`).
"""

from __future__ import annotations

from sieve.session.frontier import Frontier, Piece, fill_order
from sieve.session.ladder import (
    Attempt,
    Request,
    Situation,
    admissible,
    choose,
    coalesce,
)
from sieve.session.ledger import (
    CHOSEN_KINDS,
    COARSE_FIELD,
    DISCARDED_VALUE,
    DOUBLE_DECODE,
    PLACEHOLDER,
    PREDICTED_FETCH,
    RECOMPUTED,
    SUPERSEDED_RENDER,
    UNPAINTED,
    WASTE_KINDS,
    Account,
    Activity,
    Ledger,
    Serve,
)

__all__ = [
    "CHOSEN_KINDS",
    "Attempt",
    "Frontier",
    "Piece",
    "Request",
    "Situation",
    "admissible",
    "choose",
    "coalesce",
    "fill_order", "COARSE_FIELD", "DISCARDED_VALUE", "DOUBLE_DECODE",
    "PLACEHOLDER", "PREDICTED_FETCH", "RECOMPUTED", "SUPERSEDED_RENDER",
    "UNPAINTED", "WASTE_KINDS", "Account", "Activity", "Ledger", "Serve",
]
