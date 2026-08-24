"""Does the whole thing hold together, and does a drag ever decode?

P7 of `docs/archive/2026.08-substrate-port.md`, and the first case in this folder that
runs the substrate as one thing rather than a layer at a time. Everything below
has been checked alone; what has not been checked is the wiring, and the wiring
is where every previous version of this tree went wrong.

One property above all the others: **a drag over ground that has not been
filled causes no decode of the original.** The freeze finding measures the
alternative at two to four hundred milliseconds per drag event on the thread
that draws, and the symptom is not slowness — it is a window that has stopped
answering. The session enforces this rather than remembering it, by knowing
which thread built it and refusing.

Seven cases, none needing footage: the route is the fake one, and a proxy is a
span store filled with display-form frames.

**cold** — a drag into unfilled ground returns a stand-in or a hold and asks
the route for nothing. This is the case `--broken` fails.

**released** — the same row, with the control released, decodes and returns
exact pixels, and the result is admitted because it comes from source sampling.

**landing** — a landing fills anchored on the click, and afterwards the drag
that used to hold is a resident hit.

**crop** — a new crop is a form change: the store misses without anything being
wiped, and the old crop's frames are still there to be hit again.

**hunting** — outside the window the proxy answers and its result is *never*
admitted, because a display form is close without being the frame.

**waste** — a decode of a row whose source form is already resident is counted
as waste with an address, and an ordinary first decode is not.

**account** — the ledger's clocks close against the interval that elapsed, and
the serves that happened are on the record.

**thread** — a session built on a worker, which is how the window opens one,
is *told* which thread draws rather than guessing from its constructor. The
guess was wrong in exactly the arrangement the freeze rule asks for, and what
it silently switched off was the accounting rather than the refusal.

`--broken` restores the pre-finding viewer: the blocking decode is on every
ladder and the session's guard is removed. `cold` then decodes on the drawing
thread, once per request, and says how many times.

Run:
    uv run --group experiments python experiments/substrate-checks/08-session.py
    uv run --group experiments python experiments/substrate-checks/08-session.py --broken
"""

from __future__ import annotations

import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
import harness  # noqa: E402
from harness import Run  # noqa: E402

from sieve.analysis.tool import Tool, analysis_form  # noqa: E402
from sieve.decode import fake as fake_mod  # noqa: E402
from sieve.decode.fake import FakeRoute  # noqa: E402
from sieve.frame.form import Form, build  # noqa: E402
from sieve.session import ladder as ladder_mod  # noqa: E402
from sieve.session.ladder import (  # noqa: E402
    DECODE,
    DERIVE,
    HOLD,
    KEYFRAME,
    NEAR,
    PROXY,
    RESIDENT,
    Attempt,
    admissible,
)
from sieve.session.ladder import Request  # noqa: E402
from sieve.session.ledger import DOUBLE_DECODE, PLACEHOLDER  # noqa: E402
from sieve.session.session import BlockedTheDrawingThread, Session  # noqa: E402
from sieve.store.chunks import ChunkStore  # noqa: E402
from sieve.store.spans import SpanStore  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

ROWS = 960
CHUNK = 96
WINDOW = 288
#: contains the row marker (four blocks of MARK across the top),
#: so a served crop can still say which row it is
CROP = (0, 0, 32, 24)
PROXY_FORM = Form((0, 0, 64, 48), (32, 24), "gray")


def unguarded(self, request, tier: str) -> None:
    """The guard removed — a viewer that has not been measured yet."""
    return None


#: bound before anything is patched. Reaching for `ladder_mod.choose` inside
#: the substitute would find the substitute, which is an infinite recursion
#: rather than a broken ladder — and the traceback says nothing about what the
#: case was trying to demonstrate.
_real_choose = ladder_mod.choose


def always_blocking(request, situation, near_radius: int = 12):
    """Every ladder ends in a decode. See `07-ladder.py` for why this is the
    version somebody writes first."""
    rungs = [r for r in _real_choose(request, situation, near_radius)
             if r.tier != HOLD]
    return tuple(rungs + [Attempt(DECODE, have=situation.source_form,
                                  admit=admissible(situation.source_form,
                                                   request.want))])


def make(root: Path, *, with_proxy: bool = True) -> tuple[Session, FakeRoute]:
    table = fake_mod.table(ROWS)
    route = FakeRoute(table)
    session = Session(root / "src.mp4", root / "derived", route=route,
                      budget_bytes=600 * 64 * 48,
                      window_rows=WINDOW, rows_per_chunk=CHUNK)
    session.crop = CROP
    session.tools = [Tool(name="absdiff", form_for=analysis_form("gray"),
                          offsets=(-1, 0), field=lambda f, r: None)]
    if with_proxy:
        proxy_dir = root / "derived" / "proxy"
        proxy = ChunkStore(proxy_dir, table, rows_per_chunk=CHUNK)
        for start in range(0, ROWS, CHUNK):
            proxy.encode(PROXY_FORM, start,
                         [build(route.image(r), PROXY_FORM)
                          for r in range(start, start + CHUNK)])
        proxy.close()
        session.set_proxy(SpanStore(proxy_dir, table), PROXY_FORM)
    return session, route


def case_cold(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    session, route = make(root / "cold", with_proxy=False)
    session.window = (0, WINDOW)
    route.reset()

    tiers = []
    for row in range(40, 60):
        served = session.serve(row, task="drag")
        tiers.append(served.tier)
        if served.exact_pixels and served.tier not in (RESIDENT,):
            bad.append(f"row {row} claimed exact pixels from {served.tier}")

    if route.asked:
        bad.append(f"a drag over unfilled ground asked the route for "
                   f"{len(route.asked)} rows on the thread that draws")
    if set(tiers) - {HOLD, NEAR, PROXY}:
        bad.append(f"a drag reached {sorted(set(tiers) - {HOLD, NEAR, PROXY})}")
    run.note(f"cold: 20 drags over unfilled ground served as "
             f"{sorted(set(tiers))}, {len(route.asked)} decodes")
    session.close()
    return "cold (a drag never decodes)", 20, bad


def case_released(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    session, route = make(root / "released", with_proxy=False)
    session.window = (0, WINDOW)
    route.reset()

    served = session.serve(50, exact=True, task="drag")
    if served.image is None:
        bad.append("a released request got a hold")
    elif not served.exact_pixels:
        bad.append(f"a released request stood in with row "
                   f"{served.stood_in_for}")
    if not route.asked:
        bad.append("a released request did not decode")
    if not served.admitted:
        bad.append("a released decode was not admitted, though it comes from "
                   "source sampling")
    again = session.serve(50, task="drag")
    if again.tier != RESIDENT:
        bad.append(f"the admitted frame was not a hit next time: "
                   f"{again.tier}")
    run.note(f"released: {served.tier} in {served.ms:.2f} ms, admitted, and a "
             f"hit thereafter")
    session.close()
    return "released (decodes, and keeps it)", 2, bad


def case_landing(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    session, route = make(root / "landing", with_proxy=False)
    route.reset()

    low, high = session.land(150)
    # the constructor was handed a window length and it must be the one
    # used: a version of this stored it nowhere, so every caller that
    # passed one was ignored and got the module default instead
    if high - low != WINDOW:
        bad.append(f"a session built with window_rows={WINDOW} landed "
                   f"a window of {high - low}")
    if not low <= 150 < high:
        bad.append(f"landing on 150 opened a window at {low}..{high}")
    if low % CHUNK:
        bad.append(f"the window start {low} is not on the chunk grid")
    if session.frontier is None or not session.frontier.wait(timeout=30):
        bad.append("the fill did not finish")
    order = [p.start for p in session.frontier.order]
    holding = next(p for p in session.frontier.order
                   if p.start <= 150 < p.end)
    if order[0] != holding.start:
        bad.append(f"the fill began at {order[0]}, not the chunk holding the "
                   f"click ({holding.start})")

    served = session.serve(150, task="drag")
    if served.tier != RESIDENT:
        bad.append(f"after a fill, the clicked row served from "
                   f"{served.tier}")
    if served.image is not None and FakeRoute.row_in(served.image) != 150:
        bad.append(f"the served frame is row "
                   f"{FakeRoute.row_in(served.image)}, not 150")
    run.note(f"landing: window {low}..{high}, fill order {order}, "
             f"{session.frontier.from_route} rows decoded")
    session.close()
    return "landing (anchored, then resident)", high - low, bad


def case_crop(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    session, route = make(root / "crop", with_proxy=False)
    session.window = (0, WINDOW)
    first = session.form_for()
    session.serve(50, exact=True)
    if session.resident.get(first.key(), 50) is None:
        bad.append("the first crop's frame was not admitted")

    second = session.set_crop((0, 0, 40, 30))
    if second.key() == first.key():
        bad.append("a new crop produced the same form key")
    if session.resident.get(second.key(), 50) is not None:
        bad.append("a new crop found a frame it never stored")
    if session.resident.get(first.key(), 50) is None:
        bad.append("changing the crop wiped the previous crop's frames")

    session.set_crop(CROP)
    if session.resident.get(first.key(), 50) is None:
        bad.append("returning to the first crop is not a hit")
    run.note(f"crop: {first.key()} and {second.key()} coexist; a change misses "
             "rather than wiping, and coming back is a hit")
    session.close()
    return "crop (a form change, not an erasure)", 4, bad


def case_hunting(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    session, route = make(root / "hunt")
    session.window = (0, WINDOW)
    route.reset()

    served = session.serve(700, task="hunt")
    if served.tier != PROXY:
        bad.append(f"outside the window the hunt served from {served.tier}, "
                   "not the proxy")
    if served.admitted:
        bad.append("a display form was admitted for a crop request")
    if session.resident.get(session.form_for().key(), 700) is not None:
        bad.append("a proxy answer reached the store")
    if served.stood_in_for is None:
        bad.append("a proxy answer claimed to be exact pixels")

    session.set_proxy(None)
    fallback = session.serve(720, task="hunt")
    if fallback.tier != KEYFRAME:
        bad.append(f"with no proxy the hunt served from {fallback.tier}")
    run.note(f"hunting: proxy answered row 700 and was refused admission; "
             f"with the proxy gone the hunt fell to {fallback.tier}")
    session.close()
    return "hunting (shown, never kept)", 2, bad


def case_waste(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    session, route = make(root / "waste", with_proxy=False)
    session.window = (0, WINDOW)
    want = session.form_for()

    session.serve(30, exact=True)
    if session.ledger.waste_total():
        bad.append("an ordinary first decode was counted as waste")

    # with the source form resident, the ladder derives rather than decoding —
    # which is the behaviour, and means the waste counter should stay at zero
    answer = route.at(31)
    session.resident.put(session.source_form.key(), 31, answer[0])
    route.reset()
    derived = session.serve(31, exact=True)
    if derived.tier != DERIVE:
        bad.append(f"with a dominating form resident the request served from "
                   f"{derived.tier}, not a derivation")
    if route.asked:
        bad.append("a derivation still decoded")
    if session.ledger.waste_total():
        bad.append("deriving instead of decoding was counted as waste")

    # the counter itself, called directly: it exists for a state the ladder is
    # supposed to prevent, so the only way to exercise it is to put the state
    # there. A counter that has never fired has no demonstrated power either.
    session._count_double_decode(31, want)
    counted = session.ledger.counts()["waste"].get(DOUBLE_DECODE, 0)
    if counted != 1:
        bad.append(f"the double-decode counter fired {counted} times, not "
                   "once, on a row whose source form is resident")
    session._count_double_decode(999, want)
    if session.ledger.counts()["waste"].get(DOUBLE_DECODE, 0) != 1:
        bad.append("the counter fired for a row holding nothing")
    addresses = session.ledger.document()["waste_addresses"]
    if not addresses.get(DOUBLE_DECODE):
        bad.append("the waste was counted without an address")
    run.note(f"waste: {counted} double decode, addressed as "
             f"{addresses.get(DOUBLE_DECODE, ['-'])[0]}")
    session.close()
    return "waste (counted, with an address)", 2, bad


def case_account(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    session, route = make(root / "account", with_proxy=False)
    session.window = (0, WINDOW)
    for row in range(10, 30):
        session.serve(row, task="drag")
    session.serve(15, exact=True)

    document = session.ledger.document()
    if document["serves_seen"] != 21:
        bad.append(f"the ledger saw {document['serves_seen']} serves, not 21")
    if not document["serves"]:
        bad.append("no serves were recorded")
    tiers = {entry["tier"] for entry in document["serves"]}
    if not tiers:
        bad.append("serves were recorded without a tier")

    with session.ledger.clock("serve"):
        session.serve(40, task="drag")
    account = session.ledger.account(1000.0, "serve")
    if account.attributed_ms <= 0:
        bad.append("the serve clock recorded nothing")
    if account.unattributed_ms <= 0:
        bad.append("an interval far larger than the work had no remainder")
    run.note(f"account: {document['serves_seen']} serves over tiers "
             f"{sorted(tiers)}, remainder "
             f"{account.unattributed_share * 100:.0f}% of a made-up interval")
    session.close()
    return "account (serves and clocks recorded)", 21, bad


def case_thread(run: Run, root: Path) -> tuple[str, int, list[str]]:
    """Does the session know which thread draws, when it was built elsewhere?

    It has to be told, and the reason is the freeze rule itself. Opening a
    recording builds a frame table and races the decoders, which is seconds and
    must not run on the thread that draws — so the window builds sessions on a
    worker. A session that guessed the drawing thread from its own constructor
    then held the *worker's* identity, and everything gated on the comparison
    quietly stopped firing. The guess read as needing no caller to remember
    anything; what it actually needed was for opening to be fast.
    """
    bad: list[str] = []
    built: list = []

    def build():
        built.append(make(root / "thread", with_proxy=False))

    worker = threading.Thread(target=build)
    worker.start()
    worker.join(timeout=30)
    if not built:
        bad.append("the session was not built")
        return "thread (told, not guessed)", 0, bad

    session, route = built[0]
    here = threading.get_ident()
    if session.drawing_thread == here:
        bad.append("a session built on a worker already thought this thread "
                   "drew; the case cannot show anything")
    session.drawn_on()
    if session.drawing_thread != here:
        bad.append("drawn_on did not take this thread")

    # the accounting that depends on it: the hunt route is a chosen discard,
    # and it is only counted as one where the drawing thread is the one paying
    session.window = (0, WINDOW)
    session.serve(700, task="hunt")
    counted = session.ledger.counts()["chosen"].get(PLACEHOLDER, 0)
    if counted != 1:
        bad.append(f"a keyframe served on the drawing thread counted "
                   f"{counted} chosen discards, not one")

    # and the refusal is thread-independent, which is the half that was never
    # broken: a ladder offering a decode nobody released is wrong anywhere
    session.drawn_on(here + 1)
    try:
        session._refuse_if_drawing(
            Request(row=5, want=session.form_for(), exact=False), DECODE)
        bad.append("an unreleased decode was permitted on a thread that does "
                   "not draw; the refusal must not depend on which thread")
    except BlockedTheDrawingThread:
        pass
    session.close()
    run.note("thread: a session built on a worker is told which thread draws, "
             "and the refusal never depended on the answer")
    return "thread (told, not guessed)", 3, bad


def main() -> None:
    broken = "--broken" in sys.argv
    if broken:
        ladder_mod.choose = always_blocking
        Session._refuse_if_drawing = unguarded

    run = Run(
        experiment="P7-session" + ("-broken" if broken else ""),
        question="Does a drag over unfilled ground decode, and does anything "
                 "approximate reach a store?",
    )
    run.note("no footage: the route is the fake one and the proxy is a span "
             "store of display-form frames")
    if broken:
        run.note("RUN WITH --broken: the blocking decode is on every ladder "
                 "and the session's guard is removed — the viewer as it was "
                 "before the freeze finding. `cold` is expected to FAIL.")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        results = []
        for case in (case_cold, case_released, case_landing, case_crop,
                     case_hunting, case_waste, case_account,
                     case_thread):
            try:
                results.append(case(run, root))
            except BlockedTheDrawingThread as refused:
                results.append((f"{case.__name__} (refused)", 0,
                                [f"the session refused: {refused}"]))

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
        print("the --broken run tripped nothing: the substitutions are not "
              "being reached and these cases are not demonstrating what they "
              "claim.")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
