"""Debt machinery: the placeholder marker exception.

A placeholder is a real module at its real import path raising Owed --
the placeholder is the debt entry. Marker form rule v1 and the machinery
class are defined in docs/PLAN.md, Phase 2.
"""


class Owed(Exception):
    """This scope is owed: present debt, announced structurally.

    Raised only in marker form rule v1 (docs/PLAN.md, Phase 2 gate,
    decision 4). Deliberately not an -Error name -- a marker is not a
    fault. Caught only by the debt machinery; catching it elsewhere is
    out of contract.
    """
