"""Two steps want two forms of one instant. Does the graph decode once?

`tool-experiments/02-form-derivation.py` priced deriving against decoding
per regime. This asks the question one level up: given the declarations,
what does the pool actually do — and the answer today is that it decodes
twice, because every pool and store in this tree is keyed by the form's
*string*, and string equality is a strictly weaker relation than
`forms.grade`.

    Frames.get      key = (position, form.key())    sieve/store.py
    Pool.get        key = (row, form_key)          pool.py
    Serving._cut    form != self.held_form            sieve/serve.py
    Serving._lo     forms.grade(proxy.form, form)     sieve/serve.py

The first two are the same shape in different coordinates — a pts in
`sieve/`, an ordinal here — which is not what this experiment is about and
is worth not misreading off the table.

Only the last consults the relation, and only for the proxy. So a held
frame that EXACT-dominates the one being asked for is a miss, and the miss
goes to a decoder.

Three arrangements over the same three consumers — two analysis crops at
source sampling and a canvas wanting the whole frame at display width:

    two-cursors    each consumer reads through its own opened source, which
                   is what SIEVE ships. Nothing is shared; N consumers is N
                   decodes, each sequential and cheap.
    one-cursor     one decoder, pool keyed by exact form. The second
                   consumer's miss lands on a cursor already standing on the
                   row it wants, and a re-read of where you already are
                   is a seek.
    dominator      one decoder, the source-native plane held, every crop
                   derived from it. `grade` says EXACT for all three, so all
                   three may be admitted.

Then the two derivations themselves, priced side by side: a crop taken from
the plane (EXACT, admissible) against the same crop taken from the canvas
form, which has already been resampled (APPROX, refused). Whether the
inadmissible route is even the cheaper one is a measurement and not an
assumption; the result file carries it.

Correctness, checked rather than asserted in prose: for every consumer at a
sample of rows, the bytes derived from the plane are compared against
`forms.build` from the same plane. EXACT is a claim about bytes and nothing
in this tree had checked it.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tool-experiments"))

import harness
from fetch import Fetcher
from graph import Graph
from pool import Pool

import forms as forms_mod

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = harness.FOOTAGE / "GX010047c2_02_17_26.MP4"

START = 4000
SPAN = 100

CROP_A = (2144, 982, 1024, 1024)     #: what one step reads
CROP_B = (3300, 1200, 768, 768)      #: what the other reads
DISPLAY_W = 1328                     #: what the canvas asks for

#: how many rows to verify byte-for-byte. Every row would double
#: the wall of the arrangement that happens to run the check.
VERIFY = 5


def consumer_forms(width: int, height: int):
    a = forms_mod.Form(CROP_A, (CROP_A[2], CROP_A[3]), "gray")
    b = forms_mod.Form(CROP_B, (CROP_B[2], CROP_B[3]), "gray")
    scale = DISPLAY_W / width
    canvas = forms_mod.Form((0, 0, width, height),
                            (DISPLAY_W, int(round(height * scale)) // 2 * 2),
                            "gray")
    return a, b, canvas


def run_two_cursors(run: harness.Run, source, consumers) -> None:
    """One opened source per consumer. Nothing shared, nothing negotiated."""
    fetchers = [Fetcher(BIG) for _ in consumers]
    samples, decodes, derives = [], 0, 0
    for i in range(SPAN):
        idx = START + i
        began = time.perf_counter()
        for fetcher, (name, form) in zip(fetchers, consumers):
            plane, _ = fetcher.exact(idx)
            decodes += 1
            forms_mod.derive(plane, source, form)
            derives += 1
        samples.append((time.perf_counter() - began) * 1000.0)
    seeks = sum(f.seeks for f in fetchers)
    steps = sum(f.steps for f in fetchers)
    for f in fetchers:
        f.close()
    _record(run, "two-cursors", samples, decodes, derives, seeks, steps,
            held_bytes=sum(form.nbytes for _, form in consumers),
            note="one opened source per consumer; nothing shared")


def run_one_cursor(run: harness.Run, source, consumers) -> None:
    """One decoder, pool keyed by exact form. The status quo, shared."""
    graph = Graph()
    pool = Pool(graph, budget_bytes=8 << 30)
    fetcher = Fetcher(BIG)
    samples, decodes, derives = [], 0, 0
    for i in range(SPAN):
        idx = START + i
        began = time.perf_counter()
        for name, form in consumers:
            if pool.has(idx, form.key()):
                pool.get(idx, form.key(), by=name)
                continue
            plane, _ = fetcher.exact(idx)
            decodes += 1
            out, _ = forms_mod.derive(plane, source, form)
            derives += 1
            pool.put(idx, form.key(), out, by=name)
        samples.append((time.perf_counter() - began) * 1000.0)
        for name, form in consumers:      # one row at a time
            graph.release_row(name, idx, form.key())
        pool.sweep()
    seeks, steps = fetcher.seeks, fetcher.steps
    fetcher.close()
    _record(run, "one-cursor-exact-key", samples, decodes, derives, seeks,
            steps, held_bytes=sum(form.nbytes for _, form in consumers),
            note=("pool keyed by form.key(); a second consumer's miss is a "
                  "re-read of the row the cursor is standing on"))


def run_dominator(run: harness.Run, source, consumers, verify: bool) -> None:
    """One decoder, the plane held, every crop derived from it."""
    graph = Graph()
    pool = Pool(graph, budget_bytes=8 << 30)
    fetcher = Fetcher(BIG)
    samples, decodes, derives = [], 0, 0
    mismatches: list[str] = []
    for i in range(SPAN):
        idx = START + i
        began = time.perf_counter()
        plane = pool.get(idx, source.key(), by="plane")
        if plane is None:
            plane, _ = fetcher.exact(idx)
            decodes += 1
            pool.put(idx, source.key(), plane, by="plane")
        for name, form in consumers:
            out, how = forms_mod.derive(plane, source, form)
            if how != forms_mod.EXACT:
                raise RuntimeError(f"{form.key()} came back {how}")
            derives += 1
            pool.put(idx, form.key(), out, by="plane")
        samples.append((time.perf_counter() - began) * 1000.0)
        if verify and i < VERIFY:
            for name, form in consumers:
                out, _ = forms_mod.derive(plane, source, form)
                if not np.array_equal(out, forms_mod.build(plane, form)):
                    mismatches.append(f"{name}@{idx}")
        pool.wipe()               # per-row: this is a cost comparison
    seeks, steps = fetcher.seeks, fetcher.steps
    fetcher.close()
    note = ("the source plane EXACT-dominates all three consumers; "
            "one decode, three derives")
    if verify:
        note += (f"; bytes verified against forms.build at {VERIFY} "
                 f"rows x {len(consumers)} consumers: "
                 + ("all equal" if not mismatches
                    else f"MISMATCH {mismatches}"))
    _record(run, "dominator", samples, decodes, derives, seeks, steps,
            held_bytes=source.nbytes + sum(f.nbytes for _, f in consumers),
            note=note)
    if mismatches:
        run.note(f"EXACT derivation did not reproduce build: {mismatches}")


def probe_approx(run: harness.Run, source, consumers) -> None:
    """What a resampled form can and cannot answer for, priced and refused.

    The canvas form is already resampled, so `grade` calls every crop taken
    from it APPROX, and it is refused whatever it costs — that is the whole
    content of *derived is for looking at, decoded is for recording*. Priced
    here so the refusal is a decision with a number beside it rather than an
    assertion, and because the shape of the work is not obviously cheaper:
    the plane route slices a large array and copies, the resampled route
    slices a small one and scales it back up.
    """
    fetcher = Fetcher(BIG)
    plane, _ = fetcher.exact(START)
    canvas = [f for name, f in consumers if name == "canvas"][0]
    lo, how_lo = forms_mod.derive(plane, source, canvas)
    crop_a = [f for name, f in consumers if name == "step-a"][0]

    from_plane = []
    from_lo = []
    for _ in range(20):
        t = time.perf_counter()
        forms_mod.derive(plane, source, crop_a)
        from_plane.append((time.perf_counter() - t) * 1000.0)
        t = time.perf_counter()
        forms_mod.derive(lo, canvas, crop_a)
        from_lo.append((time.perf_counter() - t) * 1000.0)
    _, how_from_lo = forms_mod.derive(lo, canvas, crop_a)
    fetcher.close()

    run.cases.append(harness.Case(
        "derive-from-plane(EXACT)", params={"have": source.key(),
                                            "want": crop_a.key(),
                                            "grade": forms_mod.EXACT},
        samples_ms=from_plane, unit="ms per derivation"))
    harness.report(run.cases[-1])
    run.cases.append(harness.Case(
        "derive-from-canvas(APPROX, refused)",
        params={"have": canvas.key(), "want": crop_a.key(),
                "grade": how_from_lo,
                "shortfall": round(forms_mod.shortfall(canvas, crop_a), 4)},
        samples_ms=from_lo, unit="ms per derivation",
        note=("inadmissible whatever it costs: a resampled form resamples "
              "twice, and an approximate derivation may be shown and never "
              "stored. Compare the case above for whether it is even faster")))
    harness.report(run.cases[-1])
    run.note(f"canvas form from the plane grades {how_lo}; a crop taken from "
             f"the canvas form grades {how_from_lo}")


def _record(run, name, samples, decodes, derives, seeks, steps, held_bytes,
            note) -> None:
    case = harness.Case(
        name,
        params={"span": SPAN, "start": START, "consumers": 3,
                "decodes": decodes, "derives": derives,
                "seeks": seeks, "steps": steps,
                "held_mb_per_position": round(held_bytes / (1 << 20), 2)},
        samples_ms=samples,
        unit="ms per row, all consumers served",
        note=note,
    )
    run.cases.append(case)
    harness.report(case)
    print(f"      decodes={decodes} derives={derives} seeks={seeks} "
          f"steps={steps} held={round(held_bytes / (1 << 20), 1)} MB/pos")


def main() -> None:
    run = harness.Run(
        experiment="07-form-negotiation",
        question=(
            "Three consumers want three forms of one instant. Does the pool "
            "decode once and derive, and what does keying by exact form "
            "cost instead?"
        ),
    )
    run.add_footage(BIG)

    probe = Fetcher(BIG)
    width, height = probe.size
    probe.close()
    source = forms_mod.Form((0, 0, width, height), (width, height), "gray")
    a, b, canvas = consumer_forms(width, height)
    consumers = [("step-a", a), ("step-b", b), ("canvas", canvas)]

    run.note(
        "topology: source -> {step-a: crop A native gray, step-b: crop B "
        "native gray, canvas: whole frame at display width}; the crops do "
        "not contain one another, so only the source plane dominates all "
        "three")
    run.note(f"forms: plane={source.key()} a={a.key()} b={b.key()} "
             f"canvas={canvas.key()}")

    print("07 - form negotiation across the graph")
    print()
    warm = Fetcher(BIG)
    for i in range(20):
        warm.exact(START + i)
    warm.close()

    run_two_cursors(run, source, consumers)
    run_dominator(run, source, consumers, verify=True)
    run_one_cursor(run, source, consumers)
    print()
    probe_approx(run, source, consumers)
    print()

    path = run.write()
    print(f"result: {path}")


if __name__ == "__main__":
    main()
