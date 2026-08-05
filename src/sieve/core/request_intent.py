"""Why a frame was asked for, and what that entitles it to.

A frame request is not just an index. A drag position is a guess the user is
still refining; a released slider is a commitment to land on exactly that
frame; a playback tick is neither, and is walking the whole timeline. Four
separate policies read that difference, and each one used to spell it as its
own comparison against a member of this enum — so the sentence "a guess may be
answered approximately, a commitment may not" existed only as prose, with four
implementations under it. The predicates below are that sentence.

**It is here and not in `gui/transport/coalescer.py`, where the enum was born, because
the layer contract puts `bench` below `gui`.** `bench/retention_trace.py`
scores a recorded session on which requests were drags, and could not import
the symbol that answers that; it carried `SCRUB_KIND = "scrub"`, a hand-copied
member value whose drift nothing but a Qt test driving a real cursor could
notice. The coalescer's own substance — two slots, the rank arithmetic, the
generation stamp — is interaction policy and stays above; a vocabulary that
three layers read is not.
"""

from __future__ import annotations

from enum import StrEnum, auto


class RequestKind(StrEnum):
    """Why a frame was asked for."""

    #: A committed position: a released slider, a step, a menu action.
    EXACT = auto()
    #: A drag position, still being refined.
    SCRUB = auto()
    #: Driven by the playback clock.
    PLAYBACK = auto()

    @property
    def is_commitment(self) -> bool:
        """Whether the caller has promised to land on exactly this frame.

        The premise of the rank rule: a guess never displaces a commitment,
        because a playback tick or a fresh drag taking the pending slot from a
        released slider strands the user somewhere they never asked to be.
        """
        return self is RequestKind.EXACT

    @property
    def may_be_snapped(self) -> bool:
        """Whether the target may be moved to a coarse grid to meet the budget.

        Only a guess may be, and only because the user is still refining it —
        `gui/transport/scrub_policy.py` decides *when*, this decides *what is eligible*.
        """
        return self is RequestKind.SCRUB

    @property
    def may_be_retained(self) -> bool:
        """Whether the answer is worth keeping in the scrub cache.

        Playback is excluded: it walks the whole timeline once and would evict
        every frame a drag warmed, which is the grid the budget is held by.
        """
        return self is not RequestKind.PLAYBACK

    @property
    def is_felt_latency(self) -> bool:
        """Whether this round trip is latency a human is waiting on.

        Separate from `may_be_snapped` despite selecting the same member today.
        One is asked of a request going out and one of the answer coming back,
        and the reason a kind may be approximated is not the reason its round
        trip is the number `scrub_to_repaint` names — a kind added later can
        answer these differently, and collapsing them now would hide that.
        """
        return self is RequestKind.SCRUB
