"""Does the ladder put the blocking decode where it belongs, and nowhere else?

P6 of `docs/archive/2026.08-substrate-port.md`. The ladder is a pure function, so this
file is a table of cases rather than a rig — which is the entire reason the
ladder was separated from the thing that executes it. In the explorers the same
decisions are made inside `_serve`, a method on a `QMainWindow` that reads
checkbox state, and the only way to ask what it would do is to run a GUI and do
it.

Four rules, three of them from `docs/findings/2026.08.22-what-froze-the-felt-loop.md`
and each of which cost real instrumentation to find.

**The GUI thread may block only for an exact request the user just released.**
A blocking decode is not on the ladder otherwise, at all. The finding measures
this as the difference between a drag costing single-digit milliseconds and one
costing two to four hundred, and "frozen" is what the second felt like.

**Inside the window, the last resort is to hold.** A hold reads as a beat; a
blocked event loop reads as a hang. The cheap answers come first and the true
frame arrives when the fill catches up.

**Outside the window, the proxy shows and the original answers exactly.** The
proxy is a display form and can only stand in. A keyframe decode gives real
pixels at source sampling, and what is built from those is kept — the free
admission the hunt route makes possible.

**Requests coalesce by discarding.** A frame superseded before it was drawn was
never going to be seen.

Seven cases.

**released** — an exact request inside the window ends in a blocking decode,
and that decode's result is admissible because it comes from source sampling.

**dragging** — a non-exact request inside the window has no blocking tier
anywhere on its ladder and ends in a hold. This is the case `--broken` fails.

**refinement** — the non-exact ladder is ordered cheapest-first and the two
`NEAR` attempts bracket the coarse one: a nearly-right frame reads as the
moment asked for, a coarse frame reads as it blurred, and a further-off frame
beats showing nothing.

**hunting** — outside the window the proxy shows and the keyframe decode
answers, and there is no fill coming so nothing waits on one.

**admission** — nothing that grades approximate is admissible anywhere on any
ladder, and the keyframe's own product is. Checked over every case rather than
in one, because a single tier getting this right is not the property.

**forms** — a proxy that cannot cover the wanted rect at all is left off rather
than offered and refused later, and a wanted form the source cannot produce
makes the derivation and the decode inadmissible rather than absent.

**coalesce** — an arriving request replaces whatever was outstanding.

`--broken` puts the blocking decode on every ladder, which is what a viewer
does before somebody measures it.

Run:
    uv run --group experiments python experiments/substrate-checks/07-ladder.py
    uv run --group experiments python experiments/substrate-checks/07-ladder.py --broken
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
import harness  # noqa: E402
from harness import Run  # noqa: E402

from sieve.frame.form import Form  # noqa: E402
from sieve.session import ladder as ladder_mod  # noqa: E402
from sieve.session.ladder import (  # noqa: E402
    CHUNK,
    DECODE,
    DERIVE,
    HOLD,
    KEYFRAME,
    NEAR,
    PROXY,
    RESIDENT,
    Attempt,
    Request,
    Situation,
    admissible,
    choose,
    coalesce,
)

harness.RESULTS = Path(__file__).resolve().parent / "results"

SOURCE = Form((0, 0, 5312, 2988), (5312, 2988), "gray")
CROP = Form((2144, 982, 1024, 1024), (1024, 1024), "gray")
PROXY_FORM = Form((0, 0, 5312, 2988), (1328, 747), "gray")
ELSEWHERE = Form((10, 10, 200, 200), (200, 200), "gray")

INSIDE = Situation(in_window=True, source_form=SOURCE, proxy_form=PROXY_FORM)
OUTSIDE = Situation(in_window=False, source_form=SOURCE,
                    proxy_form=PROXY_FORM)


def always_blocking(request: Request, situation: Situation,
                    near_radius: int = 12) -> tuple[Attempt, ...]:
    """The ladder with the blocking decode always available.

    Kept here as the thing being argued against, and it is the obvious
    version: if the true frame can be fetched, fetch it. What it costs is
    hundreds of milliseconds on the thread that draws, once per drag event,
    and the symptom is not slowness but a window that has stopped responding.
    """
    rungs = list(choose(request, situation, near_radius))
    blocking = Attempt(DECODE, have=situation.source_form,
                       admit=admissible(situation.source_form, request.want))
    return tuple([r for r in rungs if r.tier != HOLD] + [blocking])


def tiers(attempts) -> list[str]:
    return [a.tier for a in attempts]


def case_released(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    ladder = ladder_mod.choose(Request(500, CROP, exact=True, task="drag"),
                               INSIDE)
    order = tiers(ladder)
    if order[-1] != DECODE:
        bad.append(f"a released request ends in {order[-1]}, not a decode")
    if HOLD in order:
        bad.append("a released request may hold; it is owed the true pixels")
    if order[0] != RESIDENT:
        bad.append(f"a released request starts at {order[0]}")
    if CHUNK not in order:
        bad.append("a released request does not try what is persisted first")
    decode = next(a for a in ladder if a.tier == DECODE)
    if not decode.admit:
        bad.append("the decode's own product is not admissible, though it "
                   "comes from source sampling")
    run.note(f"released: {order}")
    return "released (blocking is on this one)", len(order), bad


def case_dragging(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    ladder = ladder_mod.choose(Request(500, CROP, exact=False, task="drag"),
                               INSIDE)
    order = tiers(ladder)
    blocking = [a.tier for a in ladder if a.blocking]
    if blocking:
        bad.append(f"a request nobody released may block on {blocking}")
    if order[-1] != HOLD:
        bad.append(f"a non-exact request ends in {order[-1]}, not a hold")
    for task in ("play", "step", "scrub", "hop"):
        other = ladder_mod.choose(Request(500, CROP, exact=False, task=task),
                                  INSIDE)
        if any(a.blocking for a in other):
            bad.append(f"task {task!r} put a blocking tier on the ladder")
    run.note(f"dragging: {order} — nothing on it makes the caller wait")
    return "dragging (nothing blocks)", len(order), bad


def case_refinement(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    ladder = ladder_mod.choose(Request(500, CROP, exact=False), INSIDE)
    order = tiers(ladder)

    if order.count(NEAR) != 2:
        bad.append(f"the ladder offers {order.count(NEAR)} near attempts, not "
                   "the tight one and the loose one")
    else:
        tight, loose = [a for a in ladder if a.tier == NEAR]
        if tight.radius >= loose.radius:
            bad.append(f"the near attempts are not ordered by radius "
                       f"({tight.radius} then {loose.radius})")
        if PROXY in order:
            first = order.index(NEAR)
            coarse = order.index(PROXY)
            last = len(order) - 1 - order[::-1].index(NEAR)
            if not first < coarse < last:
                bad.append("the coarse stand-in does not sit between the "
                           "tight and loose neighbours")
    if order.index(RESIDENT) != 0 or order.index(CHUNK) != 1:
        bad.append(f"the ladder does not start with what is already here: "
                   f"{order[:2]}")
    run.note(f"refinement: {order}")
    return "refinement (cheapest first)", len(order), bad


def case_hunting(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    ladder = ladder_mod.choose(Request(9000, CROP, exact=False, task="hunt"),
                               OUTSIDE)
    order = tiers(ladder)
    if KEYFRAME not in order:
        bad.append("outside the window there is no keyframe decode on offer")
    if PROXY not in order:
        bad.append("outside the window the proxy is not offered")
    if order.index(PROXY) > order.index(KEYFRAME):
        bad.append("the keyframe decode is offered before the proxy")
    if CHUNK in order:
        bad.append("outside the window the ladder still tries chunks")
    keyframe = next(a for a in ladder if a.tier == KEYFRAME)
    if not keyframe.admit:
        bad.append("the keyframe decode's product is not admissible; bytes "
                   "that already exist are being refused")

    no_proxy = ladder_mod.choose(Request(9000, CROP, exact=False),
                                 Situation(in_window=False,
                                           source_form=SOURCE))
    if PROXY in tiers(no_proxy):
        bad.append("a proxy was offered where none exists")
    if KEYFRAME not in tiers(no_proxy):
        bad.append("with no proxy the hunt has no way to see anything")
    run.note(f"hunting: {order}; with no proxy built yet {tiers(no_proxy)}")
    return "hunting (proxy shows, original answers)", len(order), bad


def case_admission(run: Run) -> tuple[str, int, list[str]]:
    """Nothing approximate is admissible, on any ladder, ever."""
    bad: list[str] = []
    checked = 0
    for situation in (INSIDE, OUTSIDE):
        for exact in (True, False):
            for want in (CROP, SOURCE):
                ladder = ladder_mod.choose(
                    Request(500, want, exact=exact), situation)
                for attempt in ladder:
                    checked += 1
                    if attempt.have is None:
                        continue
                    if attempt.admit and not admissible(attempt.have, want):
                        bad.append(f"{attempt.tier} is admissible for "
                                   f"{want.key()} from {attempt.have.key()}, "
                                   "which is not an exact derivation")
                    if attempt.tier == PROXY and attempt.admit and \
                            want is CROP:
                        bad.append("a display form was admitted for a crop")
    run.note(f"admission: {checked} attempts across every ladder, none "
             "admissible except by an exact derivation")
    return "admission (approx is never kept)", checked, bad


def case_forms(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    # a proxy whose rect does not contain the wanted one cannot show anything
    narrow = Situation(in_window=False, source_form=SOURCE,
                       proxy_form=Form((0, 0, 100, 100), (50, 50), "gray"))
    if PROXY in tiers(ladder_mod.choose(Request(500, CROP), narrow)):
        bad.append("a proxy that cannot cover the wanted rect was offered")

    # a wanted form the source cannot produce: offered, and not admissible
    colour = Form((2144, 982, 1024, 1024), (1024, 1024), "bgr")
    ladder = ladder_mod.choose(Request(500, colour, exact=True), INSIDE)
    if DERIVE in tiers(ladder):
        bad.append("a derivation was offered from grey to colour")
    decode = next((a for a in ladder if a.tier == DECODE), None)
    if decode is None:
        bad.append("a released request for colour has no decode on it")
    elif decode.admit:
        bad.append("a grey source was said to admit a colour form")

    # a wanted form outside the source entirely
    outside_rect = Form((9000, 9000, 64, 64), (64, 64), "gray")
    ladder = ladder_mod.choose(Request(500, outside_rect, exact=True), INSIDE)
    if any(a.admit for a in ladder):
        bad.append("a rect outside the source was admissible from something")
    run.note("forms: what can be shown and what can be kept both follow from "
             "grade, so no tier needed a rule of its own")
    return "forms (grade decides, not the tier)", 3, bad


def case_coalesce(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    if coalesce([], 5) != [5]:
        bad.append("an arriving request did not become the work")
    if coalesce([1, 2, 3], 9) != [9]:
        bad.append(f"outstanding work was queued rather than discarded: "
                   f"{coalesce([1, 2, 3], 9)}")
    if len(coalesce([1, 2, 3, 4, 5, 6], 7)) != 1:
        bad.append("a burst of requests left more than one to serve")
    run.note("coalesce: a request that arrives while another is outstanding "
             "replaces it — the superseded frame was never going to be seen")
    return "coalesce (discard, not queue)", 3, bad


def main() -> None:
    broken = "--broken" in sys.argv
    if broken:
        ladder_mod.choose = always_blocking

    run = Run(
        experiment="P6-ladder" + ("-broken" if broken else ""),
        question="Is the blocking decode on exactly the requests that are "
                 "owed one, and is nothing approximate ever admissible?",
    )
    run.note("no footage and no rig: the ladder is a pure function, so this "
             "is a table of cases")
    if broken:
        run.note("RUN WITH --broken: the blocking decode is available on every "
                 "ladder, which is what a viewer does before somebody measures "
                 "it. `dragging` is expected to FAIL.")

    results = [
        case_released(run),
        case_dragging(run),
        case_refinement(run),
        case_hunting(run),
        case_admission(run),
        case_forms(run),
        case_coalesce(run),
    ]

    ok = True
    print(f"{'case':<40} {'checked':>9}  verdict")
    for label, checked, bad in results:
        ok = ok and not bad
        print(f"{label:<40} {checked:>9}  "
              f"{'ok' if not bad else f'FAIL ({len(bad)})'}")
        for line in bad[:4]:
            print(f"    {line}")
        run.note(f"{label}: {checked} checked, {len(bad)} disagreed"
                 + ("; first: " + bad[0] if bad else ""))

    print()
    for line in run.notes:
        print(f"  · {line}")

    print("\nPASS" if ok else "\nFAIL")
    if broken and ok:
        print("the --broken run tripped nothing: the substitution is not "
              "being reached and these cases are not demonstrating what they "
              "claim.")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
