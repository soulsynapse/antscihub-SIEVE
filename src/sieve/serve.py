"""Which tier answers a request, and which one did.

The tiers were built one at a time and each landed with its own branch in
whatever called it. This is the selection collected into one place, and the
answer carrying the name of the route that produced it — which is the half
the session explorer had and the port dropped. `contract/nodes.py` records
what that cost once already: every serve there travelled beside a route, the
tiers branched on it, and dropping it is what made one return value mean
four different things.

**A route is a name, not a cost class.** ADR-0007 keeps cost at the pairing
where it runs, so nothing here says what a route is worth; it says which tier
answered, so whoever times the call knows what it timed. A drag reading
`near` at 8 ms and one reading `source` at 8 ms are different facts about the
same number.

**Two callers, two rules, and the rule is the finding's.**
`docs/findings/2026.08.22-what-froze-the-felt-loop.md`: the GUI thread may
block only for an exact request the user just released. `guess` is everything
else and never reaches the source; `commit` is the exact one and may.
Blocking miss decodes on the drag path measured 200-370 ms apiece and are
what "frozen" was.

**The ladder has a rung missing and it is named rather than hidden.** Between
a held frame and holding still belongs the display proxy — a right-instant,
coarse picture, which is what makes a scrub *outside* the filled window cost
anything at all. It is absent here because nothing can produce one: a proxy
form is resampled, `forms.grade` grades it APPROX, and `forms.build` refuses
to resample because which resampler is canonical is undecided. So `guess`
runs out of tiers one position past the frontier and the picture holds. The
same gap is why `NEAR` has one threshold and not two — the explorer's second,
tighter one exists to say *a very near held frame beats the proxy*, and a
threshold whose whole job is to rank against a tier that does not exist ranks
against nothing.

Nothing here imports Qt, and nothing here holds a thread. The caller owns
both, and owes this module the rule `store.py` states: one thread calls
`commit`, because the source underneath it is not shared.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from sieve.chunks import ChunkStore
from sieve.contract.forms import Form
from sieve.contract.nodes import Refusal
from sieve.store import Store

#: How far off a held frame may be and still be shown during a drag, in listed
#: positions. The explorer's radius: near enough that the picture tracks the
#: cursor, far enough that a filling window is draggable before it is covered
#: — the frontier races the cursor, and a frame a few positions back is a
#: picture where an exact one would be a stall.
NEAR = 12


class Route(str, Enum):
    """Which tier produced a frame. Closed, and the substrate's to extend.

    Closed for the reason `Refusal` is: a consumer that branches on these
    cannot anticipate a tier minting its own name. A tier not on this list
    has found a defect in the list.
    """

    #: held in RAM at exactly this form — the tier everything else defers to
    HELD = "held"
    #: a chunk written behind an earlier fill, read back at cut speed
    CUT = "cut"
    #: a held frame within `NEAR`: right form, nearly the right instant
    NEAR = "near"
    #: the source itself, decoded now. Only an exact request may reach it.
    SOURCE = "source"
    #: the source will never deliver this position — the one route that blanks
    GONE = "gone"
    #: nothing presentable and nothing owed; the picture stays where it is
    HOLD = "hold"


@dataclass(frozen=True)
class Served:
    """A frame and the route that produced it, or a route and no frame.

    A record rather than a tuple for the reason `Answer` is one: the caller
    that draws and the caller that logs want different halves, and a pair
    unpacked positionally at four call sites is a pair unpacked backwards at
    the fifth.

    `frame` is None for `HOLD` — nothing to draw and the playhead does not
    move — and for `GONE`, where the canvas is cleared because the position
    genuinely holds nothing. Those two are opposite instructions and the
    route is what tells them apart.
    """

    frame: Any | None
    route: Route

    @property
    def drawable(self) -> bool:
        return self.frame is not None


class Ordinals:
    """A listing snapshot and the table that says what row *i* of it means.

    ADR-0004 admits an ordinal only as a per-store coordinate carried beside a
    table, and this is that table. It is deliberately *not* on `Store`, which
    holds that an extent is asked and never stored: a growing folder must move
    `Store.positions` under everything that asks. Here the snapshot is the
    point — chunks are filed by ordinal, and a grid that renumbered itself
    when a still landed would file the next chunk over the last one.

    Which also names the bug: a source still being written into grows past
    this and nothing re-takes it. `docs/vertical-slice.md` carries that as
    untested rather than as fixed.
    """

    def __init__(self, listed: tuple[int, ...]) -> None:
        self.listed = listed
        self._rank = {position: index for index, position in enumerate(listed)}

    def __len__(self) -> int:
        return len(self.listed)

    def rank(self, position: int) -> int | None:
        """Which row *position* is, or None if this listing has no such frame."""
        return self._rank.get(position)

    def around(self, position: int, radius: int,
               within: tuple[int, int] | None = None) -> tuple[int, ...]:
        """Listed positions within *radius* rows of *position*.

        In rows and never in pts, which is the mistake this exists to make
        unavailable: at 90 kHz over 23.976 fps one frame is 3753.75 ticks, so
        a pts difference compared against a count of frames reads every
        ordinary step as a jump.

        `within` clips to a half-open span of ordinals — the filled window,
        whose frames are the only ones anything holds.
        """
        here = self.rank(position)
        if here is None:
            return ()
        low, high = (0, len(self.listed)) if within is None else within
        return self.listed[max(low, here - radius):min(high, here + radius + 1)]


class Serving:
    """The tiers of one open recording, cheapest first, with names.

    Holds no thread and starts none. `held_form` is what the fill and the
    chunks are in, which is not always what the canvas asks for — the whole
    frame is the marked exception once a crop exists, and on that view the
    chunk tier cannot answer because it was never written in that form. That
    is one fact rather than the two the caller used to carry (is there a crop,
    is the whole frame showing), which could disagree.
    """

    def __init__(self, store: Store, ordinals: Ordinals) -> None:
        self.store = store
        self.ordinals = ordinals
        #: the chunks an earlier fill wrote, once there are any
        self.chunks: ChunkStore | None = None
        #: the form the fill holds and the chunks were written from
        self.held_form: Form | None = None
        #: the filled span, in ordinals. None when nothing is filled.
        self.active: tuple[int, int] | None = None

    # -- the two callers ---------------------------------------------------

    def guess(self, position: int, form: Form) -> Served:
        """A drag. Never blocks, and never reaches the source.

        The nearest tier is what makes a filling window draggable before it is
        covered. Outside a window it finds nothing and the answer is `HOLD`,
        which is honest and is the rung this ladder is missing.
        """
        held = self.store.frames.get(position, form)
        if held is not None:
            return Served(held, Route.HELD)
        near = self._near(position, form, NEAR)
        if near is not None:
            return Served(near, Route.NEAR)
        return Served(None, Route.HOLD)

    def commit(self, position: int, form: Form) -> Served:
        """A release or a playback step. This one is paid for.

        Both are exact — a step names its position as squarely as a release
        does — and both may block, because nothing here computes anything and
        a step that arrives late delays the next rather than skipping it.

        Three tiers, cheapest first. The middle one is why a window survives
        its own cache: the budget evicts, the chunks do not, and a revisited
        position costs a cut's random access rather than the original's seek
        (`docs/findings/2026.08.21-lossy-intra-beats-lossless-for-the-cut.md`
        prices the difference at 10.3 ms against 315.5).

        Only `GONE` blanks the canvas. A forward-only source asked behind its
        head refuses `LATER` — the frame exists and this consumer cannot have
        it — and clearing the picture there would report a live source's whole
        past as empty. Stepping back with `,` on one is exactly that case.
        """
        held = self.store.frames.get(position, form)
        if held is not None:
            return Served(held, Route.HELD)
        cut = self._cut(position, form)
        if cut is not None:
            self.store.frames.put(position, form, cut)
            return Served(cut, Route.CUT)
        answered = self.store.answer(position, form)
        if answered.delivered:
            return Served(answered.frame, Route.SOURCE)
        if answered.refusal is Refusal.GONE:
            return Served(None, Route.GONE)
        return Served(None, Route.HOLD)

    # -- the tiers ---------------------------------------------------------

    def _near(self, position: int, form: Form, radius: int) -> Any | None:
        """The closest held frame within *radius* rows, inside the window.

        Clipped to the filled span because that is where anything is held:
        asking outside it is a dict miss per position, and the span is three
        hundred of them.
        """
        if self.active is None:
            return None
        span = self.ordinals.around(position, radius, within=self.active)
        covered = self.store.frames.covered(span, form)
        if not covered:
            return None
        here = self.ordinals.rank(position)
        best = min(covered, key=lambda p: abs(self.ordinals.rank(p) - here))
        return self.store.frames.get(best, form)

    def _cut(self, position: int, form: Form) -> Any | None:
        """The chunk an earlier fill wrote, if it was written in this form."""
        if self.chunks is None or form != self.held_form:
            return None
        ordinal = self.ordinals.rank(position)
        return None if ordinal is None else self.chunks.fetch(ordinal)
