"""Does ranking the queue protect the person, and what does it cost the sweep?

Topology: one source, two consumers, one form.

    source ──> fill    (DEFERRED, declares a 240-position window, ordered
           │            attention-first from where the cursor starts, the
           │            way `sieve/fill.py` orders its chunks)
           └─> gui     (INTERACTIVE, declares one position, moves every tick)

Both consumers want the *same* form, so every frame the fill decodes can
serve the GUI and the comparison is about scheduling alone. What varies is
who the decoder serves next, across four arbitrations:

    equal        round-robin. Neither consumer's urgency is read. This is
                 the current model: the window fill and whatever else wants
                 frames run at whatever rate the OS gives their threads.
    ranked       `graph.pressure_queue()` — a person waiting goes first,
                 and a need inside a wider declaration yields to it.
    ranked+hold  ranked, plus the one rule the dispatcher finding names and
                 leaves unimplemented: do not leave a sequential run for a
                 position that run will reach anyway. A GUI position ahead
                 of the cursor and inside the fill's own declaration is left
                 to the fill; anything else preempts.
    two-cursors  what SIEVE actually ships. The GUI decodes through its own
                 opened source (`serve.py`'s `commit` path) and never waits
                 on the dispatcher; the fill owns the dispatcher alone. No
                 preemption exists to rank.

Two GUI motion profiles, because the dispatcher finding found the wall is
linear in seeks and a GUI that moves smoothly does not produce them:

    smooth   +1 per tick — playback, or a slow drag
    jump     a seeded walk of +-50..400 within the window — scrubbing

Measured per case: every GUI request's latency from declaration to a frame
being on hand (the number a person feels), the fill's wall to cover its
window, and the decoder's seek/step split, which is what the ranking spends.

The load here is the two consumers on one machine and nothing else. External
contention — a background encode, a second pipeline — is
`decode-experiments/07-contention` and `tool-experiments/04-under-load`, and
is deliberately not stacked on top: this experiment is about arbitration, and
a case that was slow for two reasons could not say which.
"""

from __future__ import annotations

import random
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tool-experiments"))

import harness
from fetch import Fetcher
from graph import Graph, Need, Urgency
from pool import Pool

import forms as forms_mod

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = harness.FOOTAGE / "GX010047c2_02_17_26.MP4"

#: Where the window sits. Far enough in that a seek is a real seek.
WINDOW_START = 4000
WINDOW = 240

#: The crop the consumers read. A crop rather than the full frame because
#: this experiment is about arbitration and not about memory: the decode
#: cost is the same either way, and 1 MB a frame keeps the pool honest
#: without a byte ceiling forcing evictions into the middle of a case.
CROP = (2144, 982, 1024, 1024)

#: How often the GUI asks, and how many times. Fixed across cases so every
#: case's latency distribution has the same n; the fill runs on to coverage
#: afterwards, and its wall is measured separately.
TICKS = 40
TICK_MS = 60.0
#: How long a person waits before the answer stops being an answer. A
#: request that passes this is recorded at the cap and counted as abandoned.
ABANDON_MS = 500.0

#: How far ahead of the cursor a GUI position may sit and still be left to
#: the sequential run under `ranked+hold`. Same order as `STEP_WITHIN`,
#: because that is the distance over which stepping is cheaper than seeking.
HOLD_WITHIN = 60

POLICIES = ("equal", "ranked", "ranked+hold", "two-cursors")
PROFILES = ("smooth", "jump")

#: where the person starts, and therefore where the fill starts
ANCHOR = WINDOW // 2


def _attention_first() -> tuple[int, ...]:
    """The fill's offsets, anchor first, wrapping to the window's head.

    `sieve/fill.py` orders its chunks this way and says why: the same decode
    work in a different order is the difference between a frozen landing and
    a seamless one. A fill declared head-first would put the frontier a
    hundred positions behind the cursor before anything had contended for
    anything, and every policy would then be measured against an ordering
    the product does not use.

    `graph.py` is where the offsets carry the order rather than the
    dispatcher knowing about attention: a node spells "start here" by
    rotating what it declares.
    """
    return tuple(list(range(ANCHOR, WINDOW)) + list(range(0, ANCHOR)))


class Case:
    """One (policy, profile) run: a dispatcher thread and a GUI thread."""

    def __init__(self, policy: str, profile: str, form: forms_mod.Form) -> None:
        self.policy = policy
        self.profile = profile
        self.form = form
        self.form_key = form.key()
        self.graph = Graph()
        self.pool = Pool(self.graph, budget_bytes=4 << 30)
        self.fetcher = Fetcher(BIG)
        w, h = self.fetcher.size
        self.source = forms_mod.Form((0, 0, w, h), (w, h), "gray")

        #: only `two-cursors` opens a second one, and opening it is part of
        #: what that arrangement costs
        self.gui_fetcher = Fetcher(BIG) if policy == "two-cursors" else None

        self.stop = threading.Event()
        self.covered = threading.Event()
        self.latencies: list[float] = []
        self.routes: dict[str, int] = {}
        self.abandoned = 0
        self.stale = 0
        self.served = 0
        self.turn = 0
        self.fill_wall = 0.0

    # -- the decode leaf ---------------------------------------------------

    def _decode_into(self, fetcher: Fetcher, idx: int, by: str) -> str:
        frame, how = fetcher.exact(idx)
        cropped, _ = forms_mod.derive(frame, self.source, self.form)
        self.pool.put(idx, self.form_key, cropped, by=by)
        self.routes[f"{by}:{how}"] = self.routes.get(f"{by}:{how}", 0) + 1
        return how

    # -- the dispatcher ----------------------------------------------------

    def _pick(self) -> tuple[Need, int] | None:
        """Which node to serve, and at which position. The policy lives here."""
        if self.policy == "equal":
            needs = sorted(self.graph.pressure_queue(),
                           key=lambda n: n.node_id)
            if not needs:
                return None
            #: round-robin, blind to urgency. Start where the last dispatch
            #: left off so neither consumer is systematically first.
            order = needs[self.turn % len(needs):] + needs[:self.turn % len(needs)]
            self.turn += 1
            for need in order:
                unserved = need.unserved(self.pool.has)
                if unserved:
                    return need, unserved[0]
            return None

        for need in self.graph.pressure_queue():
            unserved = need.unserved(self.pool.has)
            if not unserved:
                continue
            idx = unserved[0]
            if (self.policy == "ranked+hold"
                    and need.urgency is Urgency.INTERACTIVE
                    and self._fill_will_reach(idx)):
                #: the fill arrives here by stepping, and stepping to it now
                #: would throw away every frame between — the same decodes,
                #: none of them kept.
                continue
            return need, idx
        return None

    def _fill_will_reach(self, idx: int) -> bool:
        fill = self.graph.pressure_queue()
        for need in fill:
            if need.node_id != "fill":
                continue
            if idx not in need.needed_positions():
                return False
            at = self.fetcher.at
            return at is not None and 0 < idx - at <= HOLD_WITHIN
        return False

    def _dispatch(self) -> None:
        began = time.perf_counter()
        while not self.stop.is_set():
            picked = self._pick()
            if picked is None:
                if self._window_covered():
                    if not self.covered.is_set():
                        self.fill_wall = time.perf_counter() - began
                        self.covered.set()
                time.sleep(0.001)
                continue
            need, idx = picked
            self._decode_into(self.fetcher, idx, need.node_id)
            self.served += 1
            if not self.graph.still_wants(need.node_id, idx, self.form_key):
                self.stale += 1
            if self._window_covered() and not self.covered.is_set():
                self.fill_wall = time.perf_counter() - began
                self.covered.set()

    def _window_covered(self) -> bool:
        return len(self.pool.covered(WINDOW_START, WINDOW_START + WINDOW,
                                     self.form_key)) >= WINDOW

    # -- the person --------------------------------------------------------

    def _positions(self) -> list[int]:
        rng = random.Random(20260830)
        here = WINDOW_START + ANCHOR
        out = []
        for _ in range(TICKS):
            if self.profile == "smooth":
                here += 1
            else:
                delta = rng.choice([-1, 1]) * rng.randint(50, 400)
                here = max(WINDOW_START,
                           min(WINDOW_START + WINDOW - 1, here + delta))
            out.append(here)
        return out

    def _drive(self) -> None:
        for idx in self._positions():
            tick = time.perf_counter()
            self.graph.declare(Need("gui", idx, (0,), self.form_key,
                                    Urgency.INTERACTIVE))
            if self.gui_fetcher is not None:
                #: what `serve.py` does today: the drawing thread decodes
                #: through its own source rather than waiting on anyone.
                if not self.pool.has(idx, self.form_key):
                    self._decode_into(self.gui_fetcher, idx, "gui")
                else:
                    self.pool.get(idx, self.form_key, by="gui")
                self.latencies.append((time.perf_counter() - tick) * 1000.0)
            else:
                while True:
                    if self.pool.has(idx, self.form_key):
                        self.pool.get(idx, self.form_key, by="gui")
                        break
                    waited = (time.perf_counter() - tick) * 1000.0
                    if waited >= ABANDON_MS:
                        self.abandoned += 1
                        break
                    time.sleep(0.002)
                self.latencies.append(
                    min(ABANDON_MS, (time.perf_counter() - tick) * 1000.0))
            slack = TICK_MS / 1000.0 - (time.perf_counter() - tick)
            if slack > 0:
                time.sleep(slack)

    # -- the run -----------------------------------------------------------

    def run(self) -> None:
        self.graph.declare(Need("fill", WINDOW_START, _attention_first(),
                                self.form_key, Urgency.DEFERRED))
        dispatcher = threading.Thread(target=self._dispatch, daemon=True)
        dispatcher.start()
        self._drive()
        #: the fill runs on to coverage after the person stops, which is what
        #: makes its wall comparable across cases with different GUI loads
        self.covered.wait(timeout=180)
        self.stop.set()
        dispatcher.join(timeout=30)
        self.fetcher.close()
        if self.gui_fetcher is not None:
            self.gui_fetcher.close()

    def stats(self) -> dict:
        return {
            "fill_wall_s": round(self.fill_wall, 3),
            "gui_abandoned": self.abandoned,
            "dispatch_served": self.served,
            "stale": self.stale,
            "seeks": self.fetcher.seeks,
            "steps": self.fetcher.steps,
            "gui_seeks": (self.gui_fetcher.seeks
                          if self.gui_fetcher is not None else 0),
            "gui_steps": (self.gui_fetcher.steps
                          if self.gui_fetcher is not None else 0),
            "routes": dict(self.routes),
            "pool": self.pool.stats(),
        }


def warm(form: forms_mod.Form) -> None:
    """Decode across the window once so the first case does not pay the file.

    The container index and the OS page cache both land on whoever runs
    first, and a policy blamed for them is a policy blamed for the
    filesystem.
    """
    fetcher = Fetcher(BIG)
    w, h = fetcher.size
    source = forms_mod.Form((0, 0, w, h), (w, h), "gray")
    for idx in range(WINDOW_START, WINDOW_START + 30):
        frame, _ = fetcher.exact(idx)
        forms_mod.derive(frame, source, form)
    fetcher.close()


def main() -> None:
    run = harness.Run(
        experiment="05-priority-under-contention",
        question=(
            "With one source, one form and two consumers, does ranking the "
            "dispatch queue protect the interactive one, and what does the "
            "ranking cost the sweep in seeks?"
        ),
    )
    run.add_footage(BIG)
    run.note(
        "topology: source -> {fill: 240 positions declared attention-first "
        "from the cursor's starting position, DEFERRED; "
        "gui: 1 position, INTERACTIVE}; one form "
        f"{CROP[2]}x{CROP[3]} gray at source sampling, shared by both, so "
        "every fill decode can serve the GUI")
    run.note(
        "no external machine load is applied; the only contention is the "
        "two consumers for one decoder (or two, under two-cursors). "
        "decode-experiments/07-contention is the loaded-machine baseline")

    form = forms_mod.Form(CROP, (CROP[2], CROP[3]), "gray")

    print("05 - priority under contention")
    print()
    warm(form)

    for profile in PROFILES:
        print(f"gui profile: {profile}")
        for policy in POLICIES:
            case = Case(policy, profile, form)
            case.run()
            s = case.stats()
            harness_case = harness.Case(
                f"{policy}/{profile}",
                params={
                    "policy": policy, "gui_profile": profile,
                    "window": WINDOW, "window_start": WINDOW_START,
                    "ticks": TICKS, "tick_ms": TICK_MS,
                    "abandon_ms": ABANDON_MS,
                    "hold_within": HOLD_WITHIN if policy == "ranked+hold" else None,
                    "form": form.key(),
                },
                samples_ms=case.latencies,
                unit="ms, gui declare -> frame on hand",
                note=(f"fill_wall={s['fill_wall_s']}s "
                      f"seeks={s['seeks']}+{s['gui_seeks']} "
                      f"steps={s['steps']}+{s['gui_steps']} "
                      f"stale={s['stale']} abandoned={s['gui_abandoned']}"),
            )
            run.cases.append(harness_case)
            harness.report(harness_case)
            print(f"      {harness_case.note}")
            run.note(f"{policy}/{profile}: {s}")
        print()

    path = run.write()
    print(f"result: {path}")


if __name__ == "__main__":
    main()
