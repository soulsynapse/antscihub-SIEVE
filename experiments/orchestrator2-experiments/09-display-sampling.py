"""Two forms of one instant: what the display tier costs, and what keeps it one decode.

ADR-0017 says a frame fetched to be looked at is reduced to display sampling
*before it is copied or held*, and source sampling is kept for what will be
recorded. Every number in this folder was taken with that not done: one form,
full-frame luma at source sampling, and every consumer — the sweep, the GUI,
the step — reading the same array. `2026.08.30-a-twenty-second-full-frame-
window-costs-3.7s-and-7.1gb` is what that arrangement costs to hold.

The pool is already keyed by `(row, form_key)` and has been since V1, so two
forms resident needs nothing from it. What it needs is the thing V1 deferred
as its question 7 and answered only as a diagnosis: **every store in this tree
is keyed by the form's string, and string equality is strictly weaker than
`forms.grade`**, so a held frame that exactly dominates the one being asked
for is a miss and the miss goes to a decoder. V1 priced the three arrangements
and found the dominating plane held, everything derived, beat both on wall and
lost on bytes. That is the arrangement this folder has been running, by
accident rather than by decision: it holds the dominator and nothing else.

ADR-0017 asks for the other half — hold the *coarse* form, because that is
what the screen wants and it is a sixteenth of the bytes — and the moment it
lands the sweep stops being a producer for the step. A display-sampled row
cannot answer a source-sampled request at any quality that may be recorded
(`forms.grade` returns APPROX, and `forms.py`'s law refuses it admission), so
under two tiers the step's rows are not in the pool the sweep filled. That is
the whole risk, stated before the run: **two tiers means two decodes per row
unless something makes one decode serve both.**

## What was built, and the arrangement that was not

`Dispatcher(tiers=...)` is a map from a decodable key to an opaque callable
that makes it from what the fetcher returned. A decode produces the source
plane whatever form asked for it, so after the pick is stored the fetch thread
walks the other tiers and puts each one that `graph.wanter` says is *already
declared and unserved*. That test is the whole of the restraint: building a
form nobody asked for is retention on a guess, and
`2026.08.30-retention-pays-only-when-what-survives-is-contiguous` is what
refusing that costs to learn.

So the co-serve fires only where the two tiers' demands *overlap in row*. The
sweep declares its whole window at once; the step declares `depth` rows at a
time and advances as its arithmetic completes. The overlap is therefore the
step's request depth, and question 1 settled that depth at 1 by measuring it
under one form, where it bought no wall. Under two tiers depth is what buys
the coupling, which is the sense in which this experiment invalidates a
settled number rather than adding to it.

**The arrangement deliberately not built** is a trailing declaration: some
node holding the last N source rows behind the fill frontier so the step finds
them whenever it arrives. That is a hold on rows nobody declared, which is the
same speculation, and it would need a declarer that is not a consumer — a
readahead hint that confers no residency, which this tree has no concept of
and should not grow for one experiment. If the depths below cannot buy the
overlap, that is the thing to reach for, and it is `posix_fadvise`'s
`POSIX_FADV_WILLNEED` rather than anything invented here.

## The workload

    sweep   the whole window at the *display* form, attention-first from the
            anchor, DEFERRED. What a person scrubs through.
    step    `absdiff` at the source form over the same window, driven by a
            `Pass` at the arm's depth. What gets recorded.

Both finish lines are waited on and both are reported: the window covered at
the sweep's key, and the step's last row computed. An arm that fills fast and
computes slowly is not the same result as one that does both, and a single
"wall" would hide which.

No playhead. A scrubbing person is what the display tier is *for*, and it is
left out here on purpose: it makes the fetch thread's picks a third variable
and the question on the table is whether two tiers cost one decode or two.
The felt half is the explorer's, as it was for question 1.

## The arms

  source-only    one tier, everything at source sampling. Today, and every
                 wall in this folder.
  two-tier       sweep at display sampling 1/4, step at source, co-serve on,
                 at request depths 1 and 32.
  two-tier-follows
                 the same, with the step walking the sweep's attention-first
                 rotation instead of ascending. Added after the first run —
                 see below.
  two-tier-uncoupled
                 two tiers with the co-serve off. What a pool keyed by form
                 does when nobody writes the negotiation, and the only thing
                 that says what the negotiation is worth.
  -scrubbed      the same, with `06-two-readers`' hand on it: one INTERACTIVE
                 row at a time on a gaussian random walk that re-anchors,
                 superseding itself. Added after the first run — see below.
  -scrubbed-r2   the scrubbed arms at two readers, which is V2's core shape
                 for anything with a person in it and the arrangement a
                 one-reader number about a person is not about.

## Pre-registered

- **If two-tier holds the fill wall within noise of source-only while peak
  held bytes fall by about the sampling ratio over the window**, display
  sampling is free and ADR-0017 lands as written. "Decode once, serve many"
  survives the second form by becoming a cross-form claim, and `cofetched` is
  the count that carries it.
- **If the fill wall rises with the decode count** — toward two decodes per
  row — the tiers did not stay coupled, and the number that says why is
  `cofetched` against `served`: a co-serve rate near zero means the step's
  band and the fill frontier never met. Then the source tier cannot be a
  parallel fill and has to be driven *by* the step, with the display tier a
  consequence of its decodes rather than a fill of its own — a different
  arrangement, and one this experiment does not build.
- **If depth buys the coupling**, the depth at which `cofetched` approaches
  `served` is a real number about this workload and it costs held source bytes
  linearly, so it is a floor to report rather than a knob to turn. Question 1's
  depth of 1 was measured under one form and stops being the answer.
- **If the uncoupled arm matches the coupled one**, the negotiation is
  unnecessary here, which would mean the two fills interleave cheaply enough
  on one cursor that the second decode is not costing a seek — worth knowing,
  and it would say `STEP_WITHIN` is doing the work rather than the co-serve.

## The arm added after the first run, and why it is marked

The four outcomes above were written before anything ran. The first run
falsified the third of them in a way none of them anticipated: the co-serve
rate was **identical at depths 1, 8 and 32**, and equal to the number of rows
between the sweep's anchor and the end of its window. Depth is not what the
coupling is made of. The sweep declares attention-first — its offsets rotated
so the anchor comes first — and the step walks ascending from the bottom, so
the two consumers cross the same window in two different orders and every row
one of them reaches first is a decode the other cannot share. Where the orders
happen to agree the step rides the fill frontier: its inputs land as the sweep
passes, it computes immediately, and it is standing on the next row the sweep
is about to decode. That is self-sustaining and needs no depth at all.

So a fifth arm was added, with the step walking the sweep's rotation rather
than ascending (`Pass(order=...)`). It is marked as added afterwards because
it was, and its outcomes are pre-registered here on the same terms:

- **If following the order takes the decode count to one per row**, two tiers
  are free and what the second form costs is not the form but the
  disagreement in order. ADR-0017 lands with a rule attached: a consumer of a
  fill declares in the fill's order or pays for its own decodes.
- **If it does not**, the co-serve is riding on something other than the
  order and the first run's reading is wrong.

## The second set added after the first run

The parked arms above say what two tiers cost with nothing competing, and the
explorer said that is not the case that matters: a driven walk co-served 8
decodes of 633 where a smoke on the same build co-served every one of them.
The difference is a person, so the workload this excluded on purpose had to
come back, and it is `06-two-readers`' hand so that the two folders' people
are the same person. Its outcomes, pre-registered before it ran:

- **If the co-serve survives a person**, the parked result is the result and
  the display tier is free wherever the fill is.
- **If it does not**, the coupling is a property of an uncontended cursor and
  the question becomes what re-establishes it — the request depth is the
  candidate, because the lag between the frontier and the step is exactly what
  a deeper band spans, and it costs `depth` source rows held.

At one reader the person and the fill share a cursor, which the folder already
knows costs a fill 6.4x
(`2026.08.30-a-second-cursor-that-overlaps-costs-a-scrub-nothing`). So the
scrubbed arms are run at both counts and the two-reader pair is the one to
read: a one-reader number about a person is a number about an arrangement this
folder rejected.

The build cost is measured separately and reported beside the arms, because a
tier built on the fetch thread is time the cursor is not decoding, and the
prior art ADR-0017 accepts (`AVCodecContext.lowres`) has no such cost — it
reduces inside the decoder. This tree's codec does not offer it, so the tier
is a `forms.build` over the decoded plane, and what that costs is the gap
between the ADR's citation and its implementation.
"""

from __future__ import annotations

import random
import sys
import threading
import time
from pathlib import Path

import av
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tool-experiments"))

import harness
from harness import FOOTAGE

import forms as forms_mod
import tools as tools_mod
from dispatcher import Dispatcher, Reason
from fetch import Fetcher
from graph import Graph, Urgency
from nodes import Pass, StepNode, Sweep, following_order
from pool import Pool
from tiers import display_form, source_form, tiers

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
GOP = 24
WINDOW = 160
POOL_BUDGET = 12 << 30
CROP_RECT = (2144, 982, 1024, 1024)     #: the explorer's crop, so the step's
                                        #: derive cost is the one it feels
DIVISOR = 4                             #: display sampling, as `lowres=2`
                                        #: spells it: half in each axis twice
FINISH_TIMEOUT_S = 300.0
#: the playhead arm's hand, in `06-two-readers`'s shape so the two arms'
#: people are the same person.
SCRUB_EVERY = 0.05
SCRUB_SIGMA = 8.0
SCRUB_JUMP = 0.12
SEED = 7
REPS = 3
BUILD_SAMPLES = 20


def _source_shape():
    with av.open(str(BIG)) as container:
        stream = container.streams.video[0]
        total = stream.frames or int(
            stream.duration * stream.time_base * stream.average_rate)
        return total - GOP, stream.width, stream.height


def run_arm(name: str, width: int, height: int, start: int, end: int,
            two_tier: bool, depth: int, coserve: bool,
            follows: bool = False, playhead: bool = False,
            readers: int = 1) -> dict:
    graph = Graph()
    pool = Pool(graph, budget_bytes=POOL_BUDGET)
    source = source_form(width, height)
    display = display_form(width, height, DIVISOR) if two_tier else None
    watched = (display or source).key()

    dispatcher = Dispatcher(graph, pool, source.key(),
                            lambda _band: Fetcher(BIG),
                            recorders=2, readers=readers,
                            tiers=tiers(source, display), coserve=coserve)
    tool = tools_mod.absdiff()
    anchor = start + (end - start) // 2
    step = StepNode(tool, source, CROP_RECT, dispatcher)
    sweep = Sweep(start, end, anchor, watched, graph)
    #: the step's first row is its reach above the window's floor either way:
    #: `absdiff` at row r reads r-1, and a rotation that started below that
    #: would ask for a row outside the window in both forms.
    first = start + tool.reach
    order = (following_order(sweep.rows(), tool, first)
             if follows else None)
    walk = Pass(step, first, end, depth=depth, order=order)

    #: the same hand as `06-two-readers`: a gaussian random walk that
    #: re-anchors, declaring one INTERACTIVE row at a time and superseding
    #: itself. Its rows are the *watched* form, which is what a person looks
    #: at, so under two tiers it never asks for anything a step can read.
    stop_hand = threading.Event()

    def show(reason: Reason, ctx) -> None:
        if reason is Reason.INITIAL:
            ctx.request(ctx.row)
            return
        ctx.get(ctx.row)

    def hand() -> None:
        rng = random.Random(SEED)
        anchor = rng.randrange(start, end)
        while not stop_hand.is_set():
            if rng.random() < SCRUB_JUMP:
                anchor = rng.randrange(start, end)
            row = max(start, min(end - 1,
                                 round(rng.gauss(anchor, SCRUB_SIGMA))))
            dispatcher.get_frame("gui", row, show, Urgency.INTERACTIVE,
                                 watched, supersedes=True)
            time.sleep(SCRUB_EVERY)

    peak_bytes = 0
    peak_held = 0
    covered_at = None
    dispatcher.start()
    t0 = time.perf_counter()
    sweep.declare()
    walk.run()
    scrubbing = None
    if playhead:
        scrubbing = threading.Thread(target=hand, daemon=True)
        scrubbing.start()
    deadline = t0 + FINISH_TIMEOUT_S
    sampled = 0.0
    while time.perf_counter() < deadline:
        peak_bytes = max(peak_bytes, pool.nbytes)
        #: a tenth of the cadence of the cover check: `held_bytes` walks
        #: every resident key and the cover check is a dict scan, and the
        #: number being watched here moves on the fill's timescale.
        now = time.perf_counter()
        if now - sampled > 0.1:
            sampled = now
            peak_held = max(peak_held, pool.held_bytes())
        if covered_at is None and len(
                pool.covered(start, end, watched)) >= end - start:
            covered_at = time.perf_counter() - t0
        if covered_at is not None and walk.done.is_set():
            break
        time.sleep(0.01)
    peak_held = max(peak_held, pool.held_bytes())
    stepped_at = time.perf_counter() - t0
    stop_hand.set()
    if scrubbing is not None:
        scrubbing.join(2)
    walk.stop()
    stats = dispatcher.stats()
    pool_stats = pool.stats()
    dispatcher.stop()
    return {
        "arm": name,
        "two_tier": two_tier,
        "depth": depth,
        "coserve": coserve,
        "follows": follows,
        "playhead": playhead,
        "readers": readers,
        "tiers": stats["tiers"],
        "fill_wall_s": round(covered_at, 3) if covered_at else None,
        "step_wall_s": round(stepped_at, 3),
        "step_computed": step.computed,
        "step_rows_wanted": end - (start + tool.reach),
        "decodes": stats["served"],
        "cofetched": stats["cofetched"],
        "coserve_present": stats["coserve_present"],
        "coserve_undeclared": stats["coserve_undeclared"],
        "tier_ms": stats["tier_ms"],
        "seeks": stats["seeks"],
        "steps": stats["steps"],
        "stale": stats["stale"],
        "shared": pool_stats["shared"],
        "shared_pairs": pool_stats["shared_pairs"],
        "peak_gb": round(peak_bytes / (1 << 30), 3),
        #: what the window costs to *hold*, which is what the tier is for.
        #: `peak_gb` counts released rows nothing has swept, and a headless
        #: arm sweeps nothing.
        "peak_held_gb": round(peak_held / (1 << 30), 3),
        "end_gb": pool_stats["gb"],
        "frames_held": pool_stats["frames"],
        "expired_picks": stats["expired_picks"],
        "errors": stats["threads"] and dispatcher.errors[:3],
    }


def build_cost(width: int, height: int) -> list[dict]:
    """What one tier costs to build, per divisor, off the fetch thread.

    Reported beside the arms rather than inside them: it is a property of
    `forms.build` and this frame size, and an arm's `tier_ms` divided by its
    decodes should land on it. Where the two disagree, the fetch thread was
    doing something else.
    """
    source = source_form(width, height)
    plane = np.random.randint(0, 255, (height, width), dtype=np.uint8)
    out = []
    for divisor in (2, 4, 8):
        want = display_form(width, height, divisor)
        samples = []
        for _ in range(BUILD_SAMPLES):
            began = time.perf_counter()
            forms_mod.derive(plane, source, want)
            samples.append((time.perf_counter() - began) * 1000.0)
        ordered = sorted(samples[1:])
        out.append({"divisor": divisor,
                    "out": want.out,
                    "mb": round(want.nbytes / (1 << 20), 2),
                    "build_ms_p50": round(ordered[len(ordered) // 2], 2),
                    "samples_ms": samples})
    return out


def _med(values):
    ordered = sorted(v for v in values if v is not None)
    return ordered[len(ordered) // 2] if ordered else None


def main() -> None:
    total, width, height = _source_shape()
    start = total // 3
    end = min(start + WINDOW, total)
    source = source_form(width, height)
    display = display_form(width, height, DIVISOR)

    run = harness.Run(
        experiment="09-display-sampling",
        question="Does holding the screen's form at display sampling cost a "
                 "second decode, and what keeps it one?")
    run.add_footage(BIG)
    run.note(f"topology: source -> pool -> {{a sweep declaring rows "
             f"{start}..{end} attention-first from the midpoint at DEFERRED, "
             f"at the arm's *watched* form; an absdiff step over the same "
             f"rows at the source form, driven by a Pass at the arm's depth}}. "
             f"No playhead: the display tier is for a person and a person is "
             f"a third variable, so the felt half stays the explorer's.")
    run.note(f"forms: source {source.key()} at "
             f"{source.nbytes / (1 << 20):.1f} MB a row; display "
             f"{display.key()} at {display.nbytes / (1 << 20):.1f} MB, which "
             f"is 1/{DIVISOR} in each axis as AVCodecContext.lowres spells it.")
    run.note("core shape: 1 fetch thread, 2 recorder threads, PARALLEL mode "
             "throughout, DropAll replacement, request depth per arm. One "
             "reader because every wall this is compared against was taken at "
             "one.")
    run.note("the co-serve puts every *declared and unserved* other tier of a "
             "row from the decode that produced it; `cofetched` against "
             "`decodes` is the rate, and a rate near zero means the step's "
             "band and the fill frontier never overlapped.")
    run.note("the `-follows` arm walks the step over the sweep's "
             "attention-first rotation rather than ascending, and was added "
             "after the first run: the co-serve rate came out identical at "
             "depths 1, 8 and 32 and equal to the rows between the anchor and "
             "the window's end, which is an ordering fact and not a depth one. "
             "Its outcomes are pre-registered in the module docstring under "
             "the heading that says it arrived late.")
    run.note(f"{REPS} interleaved repeats; a single run per arm has misread "
             f"this machine's drift as an effect twice in this folder.")

    arms = [
        ("source-only", False, 1, True, False, False, 1),
        ("two-tier-d1", True, 1, True, False, False, 1),
        ("two-tier-d32", True, 32, True, False, False, 1),
        ("two-tier-d1-follows", True, 1, True, True, False, 1),
        ("two-tier-d1-uncoupled", True, 1, False, False, False, 1),
        ("source-only-scrubbed", False, 1, True, False, True, 1),
        ("two-tier-d1-follows-scrubbed", True, 1, True, True, True, 1),
        ("source-only-scrubbed-r2", False, 1, True, False, True, 2),
        ("two-tier-d1-follows-scrubbed-r2", True, 1, True, True, True, 2),
        ("two-tier-d8-follows-scrubbed-r2", True, 8, True, True, True, 2),
        ("two-tier-d32-follows-scrubbed-r2", True, 32, True, True, True, 2),
    ]
    collected: dict[str, list[dict]] = {}
    for _rep in range(REPS):
        for name, two_tier, depth, coserve, follows, playhead, readers in arms:
            collected.setdefault(name, []).append(
                run_arm(name, width, height, start, end, two_tier, depth,
                        coserve, follows, playhead, readers))

    builds = build_cost(width, height)
    run.note("build cost off the fetch thread, per divisor: " + "; ".join(
        f"1/{b['divisor']} -> {b['out'][0]}x{b['out'][1]}, {b['mb']} MB, "
        f"{b['build_ms_p50']} ms" for b in builds))
    run.cases.append(harness.Case(
        name="tier-build-cost",
        params={"builds": builds, "source": source.key()},
        samples_ms=[s for b in builds for s in b["samples_ms"]],
        unit="ms",
        note="what a tier costs to make from a decoded plane, which is the "
             "gap between ADR-0017's lowres citation and its implementation "
             "here: lowres reduces inside the decoder and costs nothing"))

    print(f"\n{'arm':<32} {'fill_s':>7} {'step_s':>7} {'decodes':>8} "
          f"{'cofetch':>8} {'seeks':>6} {'held_gb':>8} {'computed':>9}")
    for name, runs in collected.items():
        print(f"{name:<32} {str(_med([r['fill_wall_s'] for r in runs])):>7} "
              f"{_med([r['step_wall_s'] for r in runs]):>7} "
              f"{_med([r['decodes'] for r in runs]):>8} "
              f"{_med([r['cofetched'] for r in runs]):>8} "
              f"{_med([r['seeks'] for r in runs]):>6} "
              f"{_med([r['peak_held_gb'] for r in runs]):>8} "
              f"{_med([r['step_computed'] for r in runs]):>9}")
        run.note(
            f"arm {name}: fill {[r['fill_wall_s'] for r in runs]} s; step "
            f"{[r['step_wall_s'] for r in runs]} s over "
            f"{[r['step_computed'] for r in runs]} of "
            f"{runs[0]['step_rows_wanted']} rows; decodes "
            f"{[r['decodes'] for r in runs]} of which co-served "
            f"{[r['cofetched'] for r in runs]}; seeks "
            f"{[r['seeks'] for r in runs]}; co-serve declined "
            f"{[r['coserve_present'] for r in runs]} present / "
            f"{[r['coserve_undeclared'] for r in runs]} undeclared; held "
            f"{[r['peak_held_gb'] for r in runs]} GB, pool peak "
            f"{[r['peak_gb'] for r in runs]} GB; tier build "
            f"{[r['tier_ms'] for r in runs]} ms; shared "
            f"{[r['shared'] for r in runs]}.")
        run.cases.append(harness.Case(
            name=name,
            params={"repeats": REPS, "runs": runs, "window": WINDOW,
                    "divisor": DIVISOR},
            samples_ms=[], unit="see params",
            note="decodes against cofetched is the headline; peak_held_gb is "
                 "what the tier was for, and peak_gb is that plus what "
                 "nothing swept"))

    run.write()


if __name__ == "__main__":
    main()
