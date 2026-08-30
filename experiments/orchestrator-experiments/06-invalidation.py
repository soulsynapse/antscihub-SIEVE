"""When one branch of a diamond changes, what does the other branch pay?

Topology: one source, two branches at two forms, a series writer on each.

    source ──> flow (form_f = crop F, gray, native) ──> series_flow
           └─> mhi  (form_m = crop M, gray, native) ──> series_mhi

One decode serves both branches; each derives its own crop from the decoded
plane. Then something changes, and the question is how much of what is held
has to go.

Three models of invalidation:

    whole-wipe   what `sieve/session.py` does today. There is one
                 `held_form` for the session, so a crop change stops the
                 fill, drains the writer, wipes the frames and moves the
                 chunk generation. Everything held is dropped, including
                 whatever belonged to a branch that did not change.
    derived      the node whose declaration changed re-declares; the
                 refcount releases what only it held, and the pool sweeps
                 exactly that. No node is consulted about another's frames.
    dominator    derived, plus the pool also holds the source-native plane,
                 which EXACT-dominates every crop of it (`forms.grade`). A
                 crop change is then a derive rather than a decode, and what
                 it costs is the trade this model is here to price: the
                 plane is ~16x the crop.

Three events:

    param        the flow step's parameters change; no form moves.
    crop-one     the flow crop moves; the mhi crop does not. The case the
                 orchestrator README calls the interesting one.
    crop-both    the session's crop moves, which is the gesture that exists
                 in the product today. Both branches change.

Measured per (model, event): frames evicted, frames surviving, bytes held,
and the per-position wall to restore the invariant that every declared
position is on hand again.

What this experiment does not measure, and the reason it is a finding rather
than an omission: nothing here can invalidate a *value*. The graph tracks
frame lifetimes, and a series scalar is not a frame. After a parameter
change the frames are all still correct and every stored value computed
under the old parameters is wrong, and no declaration in this tree links the
two. See the note the run writes.
"""

from __future__ import annotations

import sys
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

START = 4000
SPAN = 100

#: two crops that do not contain one another, so neither branch's frames can
#: answer for the other's and only the source plane dominates both
CROP_F = (2144, 982, 1024, 1024)
CROP_M = (3300, 1200, 768, 768)
#: where the flow crop moves to. Inside the source, overlapping neither
#: held crop exactly, so nothing already on hand answers for it.
CROP_F2 = (1900, 800, 1024, 1024)
CROP_M2 = (3000, 1000, 768, 768)

MODELS = ("whole-wipe", "derived", "dominator")
EVENTS = ("param", "crop-one", "crop-both")


def forms_for(crop_f, crop_m):
    return (forms_mod.Form(crop_f, (crop_f[2], crop_f[3]), "gray"),
            forms_mod.Form(crop_m, (crop_m[2], crop_m[3]), "gray"))


class World:
    """A pool, a graph, a decoder, and the two branches declaring into it."""

    def __init__(self, model: str) -> None:
        self.model = model
        self.graph = Graph()
        self.pool = Pool(self.graph, budget_bytes=8 << 30)
        self.fetcher = Fetcher(BIG)
        w, h = self.fetcher.size
        self.source = forms_mod.Form((0, 0, w, h), (w, h), "gray")
        self.source_key = self.source.key()
        self.derives = 0
        self.decodes = 0

    # -- filling -----------------------------------------------------------

    def declare(self, form_f: forms_mod.Form, form_m: forms_mod.Form) -> None:
        offsets = tuple(range(SPAN))
        self.graph.declare(Need("flow", START, offsets, form_f.key(),
                                Urgency.DEFERRED))
        self.graph.declare(Need("mhi", START, offsets, form_m.key(),
                                Urgency.DEFERRED))
        if self.model == "dominator":
            #: the plane is declared by a node of its own, because something
            #: has to hold it: no consumer wants the whole frame, and a tier
            #: nobody declared is exactly the ad-hoc lifetime the graph is
            #: supposed to remove.
            self.graph.declare(Need("plane", START, offsets, self.source_key,
                                    Urgency.DEFERRED))

    def serve(self, form_f: forms_mod.Form, form_m: forms_mod.Form) -> list[float]:
        """Bring every declared position on hand. Returns per-position ms."""
        samples: list[float] = []
        for i in range(SPAN):
            idx = START + i
            began = time.perf_counter()
            self._serve_one(idx, form_f, form_m)
            samples.append((time.perf_counter() - began) * 1000.0)
        return samples

    def _serve_one(self, idx: int, form_f, form_m) -> None:
        wants = [("flow", form_f), ("mhi", form_m)]
        missing = [(who, f) for who, f in wants
                   if not self.pool.has(idx, f.key())]
        if self.model == "dominator":
            plane = self.pool.get(idx, self.source_key, by="plane")
            if plane is None:
                plane, _ = self.fetcher.exact(idx)
                self.decodes += 1
                self.pool.put(idx, self.source_key, plane, by="plane")
            for who, form in missing:
                out, how = forms_mod.derive(plane, self.source, form)
                if how != forms_mod.EXACT:
                    raise RuntimeError(f"{how} may not be admitted: {form.key()}")
                self.derives += 1
                self.pool.put(idx, form.key(), out, by="plane")
            return
        if not missing:
            return
        plane, _ = self.fetcher.exact(idx)
        self.decodes += 1
        for who, form in missing:
            out, how = forms_mod.derive(plane, self.source, form)
            if how != forms_mod.EXACT:
                raise RuntimeError(f"{how} may not be admitted: {form.key()}")
            self.derives += 1
            self.pool.put(idx, form.key(), out, by=who)

    # -- the event ---------------------------------------------------------

    def invalidate(self, event: str, form_f, form_m) -> tuple[int, int]:
        """Apply *event*. Returns (evicted, surviving)."""
        before = len(self.pool)
        if event == "param":
            #: a parameter change moves no form. Under every model the
            #: frames are still exactly right, and nothing here can mark the
            #: values computed from them as stale.
            evicted = self.pool.sweep()
            return evicted, len(self.pool)

        if self.model == "whole-wipe":
            self.pool.wipe()
            return before, 0

        if event == "crop-one":
            self.graph.declare(Need("flow", START, tuple(range(SPAN)),
                                    form_f.key(), Urgency.DEFERRED))
        else:
            self.graph.declare(Need("flow", START, tuple(range(SPAN)),
                                    form_f.key(), Urgency.DEFERRED))
            self.graph.declare(Need("mhi", START, tuple(range(SPAN)),
                                    form_m.key(), Urgency.DEFERRED))
        evicted = self.pool.sweep()
        return evicted, len(self.pool)

    def close(self) -> None:
        self.fetcher.close()


def one(run: harness.Run, model: str, event: str) -> None:
    form_f, form_m = forms_for(CROP_F, CROP_M)
    world = World(model)
    world.declare(form_f, form_m)
    world.serve(form_f, form_m)

    held_before = len(world.pool)
    bytes_before = world.pool.nbytes
    decodes_before, derives_before = world.decodes, world.derives

    if event == "param":
        after_f, after_m = form_f, form_m
    elif event == "crop-one":
        after_f, after_m = forms_for(CROP_F2, CROP_M)
    else:
        after_f, after_m = forms_for(CROP_F2, CROP_M2)

    evicted, surviving = world.invalidate(event, after_f, after_m)

    #: the invariant every model owes: after the change, every position a
    #: consumer declares is on hand again
    world.declare(after_f, after_m)
    samples = world.serve(after_f, after_m)

    case = harness.Case(
        f"{model}/{event}",
        params={
            "model": model, "event": event, "span": SPAN, "start": START,
            "form_flow": after_f.key(), "form_mhi": after_m.key(),
            "held_before": held_before, "evicted": evicted,
            "surviving": surviving,
            "gb_before": round(bytes_before / (1 << 30), 3),
            "gb_after": round(world.pool.nbytes / (1 << 30), 3),
            "refill_decodes": world.decodes - decodes_before,
            "refill_derives": world.derives - derives_before,
        },
        samples_ms=samples,
        unit="ms per position, restoring the invariant",
        note=(f"evicted={evicted} surviving={surviving} "
              f"refill: {world.decodes - decodes_before} decodes / "
              f"{world.derives - derives_before} derives, "
              f"{round(world.pool.nbytes / (1 << 30), 2)} GB held after"),
    )
    run.cases.append(case)
    harness.report(case)
    print(f"      {case.note}")
    world.close()


def main() -> None:
    run = harness.Run(
        experiment="06-invalidation",
        question=(
            "When one branch of a diamond is invalidated, how much of the "
            "other branch survives, and what does restoring the invariant "
            "cost under a whole-wipe, a derived, and a dominator model?"
        ),
    )
    run.add_footage(BIG)
    run.note(
        "topology: source -> {flow at crop F, mhi at crop M}, both gray at "
        "source sampling, one decode serving both; the dominator model adds "
        "a 'plane' node holding the source-native form that EXACT-dominates "
        "both crops")
    run.note(
        "nothing here invalidates a value. After the 'param' event every "
        "held frame is still correct and every series scalar computed under "
        "the old parameters is wrong; the graph tracks frame lifetimes and "
        "no declaration in this tree links a stored scalar to the "
        "declaration that produced it. That gap is the result of this "
        "experiment's third question, not an omission from it.")

    print("06 - invalidation as a graph operation")
    print()
    for event in EVENTS:
        print(f"event: {event}")
        for model in MODELS:
            one(run, model, event)
        print()

    path = run.write()
    print(f"result: {path}")


if __name__ == "__main__":
    main()
