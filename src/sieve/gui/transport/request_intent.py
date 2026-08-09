"""Why a frame was asked for, and what that entitles it to.

A frame request is not just an index. A drag position is a guess the user is
still refining; a released slider is a commitment to land on exactly that
frame; a playback tick is neither, and is walking the whole timeline. Five
separate policies read that difference, and each one would otherwise spell it
as its own comparison against a member of this enum — so the sentence "a guess
may be answered approximately, a commitment may not" would exist only as prose,
with four implementations under it. The predicates below are that sentence.
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
        `scrub_policy.py` decides *when*, this decides *what is eligible*.
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
    def may_be_rendered(self) -> bool:
        """Whether the viewport may pay a pipeline render for this frame.

        A drag is refused one, and not because the picture would be wrong: the
        render sits inside the round trip whose latency `scrub_to_repaint`
        names, and that number is also `ScrubPolicy`'s degradation trigger — so
        a pipeline slow enough would snap the *transport* onto a coarse grid,
        which is a remedy aimed at decode. The drag shows the decoded frame and
        the release, being a commitment, is what buys the exact picture.

        Playback is not a drag in flight and keeps its render per displayed
        frame: it already drops what it cannot decode, so the cost lands on the
        achieved rate rather than on a gesture's latency.

        Separate from `may_be_snapped` despite being its complement today, for
        the reason spelled out below: one is asked of the target a request is
        sent for and this is asked of what the answer is allowed to cost.
        """
        return self is not RequestKind.SCRUB

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
