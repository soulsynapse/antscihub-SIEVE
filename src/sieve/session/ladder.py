"""Choosing what to try, in what order, and what may be kept.

The one piece of the substrate that is only a decision. It decodes nothing,
reads no file, holds no lock and touches no store: given a request and the
shape of the situation it is being made in, it returns the ordered attempts a
caller should make. That is what turns the rules below from comments inside a
widget into a table of cases.

**An ordered list, not a single choice.** A ladder that returned one tier would
have to know what is resident, which means either a scan per request or a
snapshot that is stale between the deciding and the using. Attempting each tier
in turn makes the attempt *be* the query, and the explorers already work this
way — what they lack is any way to see the order without watching a picture.

**Admissibility is `form.grade`, not a rule about routes.** Whether an attempt's
result may be kept is computed from the form it would produce against the form
that was wanted: `EXACT` may be recorded, `APPROX` may only be shown. The
explorer hard-codes that the proxy never feeds the crop store; here that falls
out, and so does its mirror image — the crop sliced from a full keyframe decode
*is* admissible, because bytes that already exist are never refused.

The four rules this encodes were each expensive to find, and three of them are
`docs/findings/2026.08.22-what-froze-the-felt-loop.md`:

1. **The GUI thread may block only for an exact request the user just
   released.** A blocking decode is simply not on the ladder otherwise. This is
   the difference between a drag that costs milliseconds and one that costs
   hundreds of them, and "frozen" is what the second feels like.
2. **Inside the window, cheaper answers come first and the last of them is to
   hold.** Resident, then persisted, then a derivation from something already
   held, then a neighbouring frame, then a coarse stand-in, then the current
   picture. A hold reads as a beat; a blocked event loop reads as a hang.
3. **Outside the window, the proxy answers and the original answers exactly.**
   The proxy is a display form and can only stand in; a keyframe decode gives
   real pixels at source sampling, from which the wanted form is built and kept.
4. **Requests coalesce by discarding, never by queueing.** A frame that has been
   superseded before it was drawn was never going to be seen, and drawing it
   costs the one after it (`docs/decode/ideas.md`).
"""

from __future__ import annotations

from dataclasses import dataclass

from sieve.frame.form import APPROX, EXACT, Form, grade

# ── the tiers, in no particular order; the order is `choose`'s to say ────
RESIDENT = "resident"    #: already in memory at the wanted form
CHUNK = "chunk"          #: a persisted span at the wanted form
DERIVE = "derive"        #: build the wanted form from something already held
NEAR = "near"            #: a neighbouring row at the wanted form, shown only
PROXY = "proxy"          #: a display-form span, shown only
KEYFRAME = "keyframe"    #: one decode at the keyframe at or before the row
DECODE = "decode"        #: a blocking exact decode of the original
HOLD = "hold"            #: change nothing; let the fill arrive

TIERS = (RESIDENT, CHUNK, DERIVE, NEAR, PROXY, KEYFRAME, DECODE, HOLD)


@dataclass(frozen=True)
class Attempt:
    """One thing to try, and what may be done with the result."""

    tier: str
    #: what this attempt would produce, before deriving. `None` where the tier
    #: produces the wanted form directly.
    have: Form | None = None
    #: may the result be recorded, or only shown? Computed from the forms
    #: rather than declared, so no tier is special.
    admit: bool = False
    #: how far a stand-in may sit from the row asked for, for the tiers that
    #: accept one. Ignored by the rest.
    radius: int = 0

    @property
    def blocking(self) -> bool:
        """Does this attempt make the caller wait on a decode of the original?"""
        return self.tier in (KEYFRAME, DECODE)


@dataclass(frozen=True)
class Request:
    """What is wanted, and whether waiting for it is permitted."""

    row: int
    want: Form
    #: the user released a control and is owed the true pixels. The only state
    #: in which a blocking decode is on the ladder at all.
    exact: bool = False
    task: str = "step"


@dataclass(frozen=True)
class Situation:
    """The shape of the world the request is made in. No live store state.

    Deliberately small. Anything that changes between deciding and using —
    what is resident, what has been persisted since — belongs in the attempt
    rather than in the decision, because a decision made against a snapshot is
    wrong exactly as often as the snapshot is stale.
    """

    in_window: bool
    #: what a route hands back: the whole frame at source sampling. Whether the
    #: wanted form can be built from it is `grade`'s to say, not a flag.
    source_form: Form
    #: the display proxy's form, where one exists for this source.
    proxy_form: Form | None = None
    #: whether anything has been persisted for this form yet. False skips a
    #: tier that is certain to miss rather than making the caller find out.
    have_chunks: bool = True


def admissible(have: Form, want: Form) -> bool:
    """May a result in `have` be recorded as `want`?

    `EXACT` only. An approximate derivation is close without being the frame,
    and a store that accepted one would hold values whose bytes depended on
    which tier happened to answer — the hazard `frame.form` exists to close.
    """
    return grade(have, want) == EXACT


def choose(request: Request, situation: Situation,
           near_radius: int = 12) -> tuple[Attempt, ...]:
    """The attempts to make, in order, for one request.

    Pure. The caller walks this list, tries each, and stops at the first that
    answers; whether an answer may be kept is on the attempt.
    """
    want = request.want
    attempts: list[Attempt] = []

    if situation.in_window:
        attempts.append(Attempt(RESIDENT, have=want, admit=False))
        if situation.have_chunks:
            attempts.append(Attempt(CHUNK, have=want, admit=False))
        # something already held at source sampling can produce the wanted
        # form exactly; that is worth trying before any stand-in
        if admissible(situation.source_form, want):
            attempts.append(Attempt(DERIVE, have=situation.source_form,
                                    admit=True))
        if not request.exact:
            # progressive refinement: a nearly-right frame reads as the moment
            # asked for, a coarse one reads as the moment blurred, and the true
            # frame arrives when the fill catches up
            attempts.append(Attempt(NEAR, have=want, admit=False,
                                    radius=min(3, near_radius)))
            approximate = _proxy_attempt(situation, want)
            if approximate is not None:
                attempts.append(approximate)
            attempts.append(Attempt(NEAR, have=want, admit=False,
                                    radius=near_radius))
            attempts.append(Attempt(HOLD))
            return tuple(attempts)
        # released: the true pixels are owed, and this is the one place a
        # blocking decode belongs
        attempts.append(Attempt(DECODE, have=situation.source_form,
                                admit=admissible(situation.source_form, want)))
        return tuple(attempts)

    # outside the window there is no fill coming, so a stand-in is not a
    # placeholder for anything — it is the answer until somebody lands
    attempts.append(Attempt(RESIDENT, have=want, admit=False))
    approximate = _proxy_attempt(situation, want)
    if approximate is not None:
        attempts.append(approximate)
    # a keyframe decode is one decode, gives real pixels at source sampling,
    # and what is built from it is kept: bytes that already exist are never
    # refused
    attempts.append(Attempt(KEYFRAME, have=situation.source_form,
                            admit=admissible(situation.source_form, want)))
    attempts.append(Attempt(HOLD))
    return tuple(attempts)


def _proxy_attempt(situation: Situation, want: Form) -> Attempt | None:
    """The display proxy, if it exists and can show anything for this form."""
    if situation.proxy_form is None:
        return None
    how = grade(situation.proxy_form, want)
    if how is None:
        return None      # the region or the format is not there at any quality
    return Attempt(PROXY, have=situation.proxy_form, admit=how == EXACT)


def coalesce(pending: list[int], row: int) -> list[int]:
    """What is left to serve once `row` is asked for. Discard, never queue.

    A frame superseded before it was drawn was never going to be seen, and
    drawing it costs the one after it — so a request that arrives while
    another is outstanding replaces it rather than joining a line. This is
    where the naive viewer and the architecture differ, and it is one line in
    both, which is why it is worth having somewhere it can be checked.
    """
    return [row]


def blocking_allowed(request: Request) -> bool:
    """May this request be served on the thread that draws?

    The single rule, stated once so no caller re-derives it: only an exact
    request the user just released. Everything else has a cheaper answer on
    its ladder and lets the fill overtake it.
    """
    return request.exact
