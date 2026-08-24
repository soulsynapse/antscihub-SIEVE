"""G3, G5 and G6. What the joints cost, what reuse is worth, and what keys it.

Three goals in one file because they want the same rig: a graph that actually
runs over real frames. Building it three times would have produced three graphs
that differ in ways nobody chose.

**Isolated, and therefore not a felt cost.** Frames are decoded once into a
dictionary and every case runs over resident arrays, single-threaded, with no
store, no fill and no drawing. That is the right instrument for these three
questions — what is being compared is arithmetic against arithmetic — and it is
the wrong instrument for anything about the loop. This folder inherits
`tool-experiments`' rule verbatim: a number claimed about the loop is taken in
the loop, and a number taken in isolation says so. This one says so.

## G3 — what the joints cost

The corrected question. Not whether a deep graph holds rate, which is about the
tools, but what generality costs when the work is held constant: dispatch, the
assembly of an input dictionary per node, and an intermediate array that a fused
function would never have named.

`fused` and `staged` do the same arithmetic — blur two rows, difference them —
and both *recompute* the upstream. Holding the policy constant is what makes the
difference the joints rather than the caching, and it is why G5 is a separate
case rather than a column of this one.

## G5 — what reuse is worth, and what it costs

A downstream node reading an upstream one at several offsets makes the upstream
run several times per position unless something keeps it. `absdiff` over an
upstream needs it twice, `lag_mhi` four times, so the reuse factor is a
declaration rather than a guess.

The compute saved is straightforward. What it is spent on is not: an
intermediate is the same size as a frame, so storing one costs frame-cache
capacity, and in the regime where decode is expensive that capacity is what
prevents decodes. That is the same shape as `02-form-derivation`'s inversion and
for a related reason, so the `crossover` case turns the trade into the one
question a scheduler could actually answer — how expensive a decode has to be
before those bytes are better spent on frames.

## G6 — what keys it

Two graphs differing only in an upstream parameter, with an identical sink. A
key folding the whole subgraph tells them apart; a key folding only the sink's
own params does not, and the second graph reads the first's numbers. `--broken`
uses the local key, which is what the tool explorer's blur chaining does today
for the one node where it happens to be safe.

Run:
    uv run --group experiments python experiments/chain-experiments/03-joints-and-reuse.py
    uv run --group experiments python experiments/chain-experiments/03-joints-and-reuse.py --broken
"""

from __future__ import annotations

import hashlib
import sys
import time
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
import harness  # noqa: E402
from harness import FOOTAGE, Case, Run, quantiles  # noqa: E402

from sieve.analysis.tool import analysis_form  # noqa: E402
from sieve.decode.pyav import software  # noqa: E402
from sieve.frame import FrameTable  # noqa: E402
from sieve.frame.form import build as build_form  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
#: the same crop `10-parity` uses, so a number here can be read beside one there
CROP = (2144, 982, 1024, 1024)
BASE_ROW = 1439
#: rows decoded and held. Enough that a 30-row reach has somewhere to reach.
ROWS = 220
#: positions each timed case evaluates, leaving room for the deepest reach
POSITIONS = 120
BLUR_K = 5
LAGS = (30, 20, 10)


# ── the graph ────────────────────────────────────────────────────────────────
SOURCE = "source"


@dataclass(frozen=True)
class Node:
    """A declaration and the work behind it. `op` reads a dict per input."""

    name: str
    offsets: tuple[int, ...]
    op: Callable[..., np.ndarray]
    inputs: tuple[str, ...] = (SOURCE,)
    params: tuple[tuple[str, str], ...] = ()

    def local_key(self) -> str:
        bits = ",".join(f"{k}={v}" for k, v in self.params)
        return f"{self.name}({bits})" if bits else self.name


@dataclass
class Graph:
    nodes: dict[str, Node] = dc_field(default_factory=dict)

    def add(self, node: Node) -> "Graph":
        self.nodes[node.name] = node
        return self


def subgraph_key(graph: Graph, name: str) -> str:
    """The durable spelling of a node *and everything it derives from*.

    Hashed rather than concatenated because the string grows with depth and a
    key is a filename. Readable prefix in front for the same reason
    `analysis/series.py` keeps one — a directory of hashes is unreadable, and a
    directory of hashes with names in front is a directory somebody can debug.
    """
    node = graph.nodes[name]
    ups = "+".join(
        SOURCE if up == SOURCE else subgraph_key(graph, up)
        for up in node.inputs)
    offs = ",".join(str(o) for o in node.offsets)
    spelling = f"{node.local_key()}[{offs}]<{ups}>"
    digest = hashlib.blake2b(spelling.encode("utf-8"), digest_size=8).hexdigest()
    return f"{node.name}-{digest}"


def local_only_key(graph: Graph, name: str) -> str:
    """The sink's own params, with nothing upstream folded in. The bug."""
    return graph.nodes[name].local_key()


# ── the work, real ops on real arrays ────────────────────────────────────────
def blur_op(frames: dict[int, np.ndarray], row: int, k: int = BLUR_K):
    return cv2.GaussianBlur(frames[row], (k, k), 0)


def absdiff_op(inputs: dict[int, np.ndarray], row: int):
    return cv2.absdiff(inputs[row - 1], inputs[row])


def mhi_op(inputs: dict[int, np.ndarray], row: int):
    """`lag_mhi`'s arithmetic, carried with the comment it earned.

    `convertScaleAbs`, not `* weight`: a Python float is a double, so
    multiplying a uint8 image by one silently promotes the whole image.
    """
    cur = inputs[row]
    out = None
    for rank, lag in enumerate(sorted(LAGS, reverse=True)):
        weight = (rank + 1) / len(LAGS)
        aged = cv2.convertScaleAbs(cv2.absdiff(cur, inputs[row - lag]),
                                   alpha=weight)
        out = aged if out is None else cv2.max(out, aged)
    return out


def blur_node(k: int = BLUR_K) -> Node:
    return Node("blur", (0,), lambda f, r: blur_op(f, r, k),
                params=(("k", str(k)),))


def diff_node() -> Node:
    return Node("diff", (-1, 0), absdiff_op, inputs=("blur",))


def mhi_node() -> Node:
    return Node("mhi", tuple(sorted(-lag for lag in LAGS) + [0]), mhi_op,
                inputs=("blur",), params=(("lags", "-".join(map(str, LAGS))),))


# ── two policies for an intermediate ─────────────────────────────────────────
def evaluate_recompute(graph: Graph, sink: str, row: int,
                       frames: dict[int, np.ndarray]) -> np.ndarray:
    """Run the graph, recomputing every upstream value on every demand.

    The generic path: assemble a dict per node, call the op, return the array.
    Every joint this file is measuring is in here.
    """
    node = graph.nodes[sink]
    gathered: dict[int, np.ndarray] = {}
    for off in node.offsets:
        want = row + off
        if node.inputs == (SOURCE,):
            gathered[want] = frames[want]
        else:
            gathered[want] = evaluate_recompute(
                graph, node.inputs[0], want, frames)
    return node.op(gathered, row)


def evaluate_stored(graph: Graph, sink: str, row: int,
                    frames: dict[int, np.ndarray],
                    kept: dict[tuple[str, int], np.ndarray]) -> np.ndarray:
    """The same walk, keeping every intermediate it produces.

    `kept` is handed in rather than made here so a caller can measure what it
    grew to, which is the half of the trade that is not time.
    """
    node = graph.nodes[sink]
    gathered: dict[int, np.ndarray] = {}
    for off in node.offsets:
        want = row + off
        if node.inputs == (SOURCE,):
            gathered[want] = frames[want]
            continue
        up = node.inputs[0]
        got = kept.get((up, want))
        if got is None:
            got = kept[(up, want)] = evaluate_stored(
                graph, up, want, frames, kept)
        gathered[want] = got
    return node.op(gathered, row)


def fused_diff(frames: dict[int, np.ndarray], row: int, k: int = BLUR_K):
    """blur → absdiff as one function, recomputing the blur exactly as the
    staged version does. No dict assembly, no dispatch, no named intermediate
    beyond what the arithmetic itself needs."""
    return cv2.absdiff(cv2.GaussianBlur(frames[row - 1], (k, k), 0),
                       cv2.GaussianBlur(frames[row], (k, k), 0))


# ── setup ────────────────────────────────────────────────────────────────────
def decode_window(run: Run) -> dict[int, np.ndarray]:
    """Decode a contiguous run once, at the analysis form, and hold it."""
    table = FrameTable.cached(BIG)
    form = analysis_form("gray")(CROP)
    route = software(BIG, table, pix="gray")
    frames: dict[int, np.ndarray] = {}
    start = BASE_ROW - max(LAGS) - 10
    t0 = time.perf_counter()
    try:
        for row in range(start, start + ROWS):
            got = route.at(row)
            if got is None:
                break
            frames[row] = build_form(got[0], form)
    finally:
        route.close()
    spent = (time.perf_counter() - t0) * 1000.0
    per = spent / max(1, len(frames))
    run.note(f"decoded {len(frames)} rows at {form.key()} in {spent:.0f} ms "
             f"({per:.2f} ms/frame, sequential software decode) — the figure "
             "the crossover case is expressed against")
    return frames, form, per


def timed(fn, rows, reps: int = 3) -> list[float]:
    """Per-position milliseconds over `reps` walks, warm-up dropped from each.

    Pooled rather than averaged per walk: the harness keeps every sample and
    takes its quantiles at read time, so collapsing the distribution here would
    throw away the only thing that says whether a difference is a difference.

    Repeated because single walks put the saving for a four-offset node above
    and below the saving for a two-offset one on consecutive runs, which is a
    spread rather than a result.
    """
    out: list[float] = []
    for _ in range(max(1, reps)):
        walked: list[float] = []
        for row in rows:
            t0 = time.perf_counter()
            fn(row)
            walked.append((time.perf_counter() - t0) * 1000.0)
        out.extend(walked[WARMUP:])
    return out


#: positions discarded before a policy is timed. It has to cover the deepest
#: reach in play: a node keeping intermediates is still *filling* until the
#: playhead has moved past its own reach, and timing that reports the cost of
#: building a cache as though it were the cost of having one. The first version
#: of this file discarded five against a reach of thirty, which made keeping an
#: intermediate look barely worth doing.
WARMUP = max(LAGS) + 10


def keep(run: Run, name: str, samples: list[float], **params) -> None:
    """File the samples that were actually taken.

    Directly rather than through `time_case`, which times the steps of an
    iterable it is handed and cannot be given a list of durations somebody
    already has. An earlier version called it with a two-element dummy iterable
    and put the real figure in `params`, which files a case whose samples are
    not the measurement — the exact shape of a result that lies.
    """
    run.cases.append(Case(name=name, params=dict(params), samples_ms=samples,
                          unit="ms per position"))


# ── cases ────────────────────────────────────────────────────────────────────
def case_joints(run: Run, frames, form) -> tuple[str, int, list[str]]:
    """G3: what an edge costs when the work is held constant.

    Measured at two array sizes, because one of them cannot answer.

    At the analysis form the joints turn out smaller than the run-to-run spread
    of the work itself. The first version of this case asserted that fused must
    beat staged and failed on a run where staged came out ahead by three
    percent — noise being read as a result. Below the noise floor is a
    legitimate answer, so the case now measures the floor and reports the
    figure against it rather than tripping over it.

    The per-edge number is therefore taken where it resolves: a chain of
    trivial nodes over a tiny array, where the work is small enough that the
    dispatch, the dict assembly and the named intermediate are most of what is
    left. That is the figure a plugin surface actually pays per edge, and the
    one to multiply by a plausible depth.
    """
    bad: list[str] = []
    rows = list(range(BASE_ROW, BASE_ROW + POSITIONS))

    # -- where a joint resolves: a small array and several edges
    small = {r: cv2.resize(a, (64, 64)) for r, a in frames.items()}
    edges = 4
    chain = Graph().add(Node("n0", (0,), lambda f, r: f[r] + 0))
    for i in range(1, edges + 1):
        chain.add(Node(f"n{i}", (0,), lambda f, r: f[r] + 0,
                       inputs=(f"n{i - 1}",)))

    def fused_chain(row):
        out = small[row] + 0
        for _ in range(edges):
            out = out + 0
        return out

    flat = timed(fused_chain, rows)
    deep = timed(lambda r: evaluate_recompute(chain, f"n{edges}", r, small),
                 rows)
    per_edge = (quantiles(deep)["p50"] - quantiles(flat)["p50"]) / edges
    if per_edge <= 0:
        bad.append(f"a {edges}-edge chain did not measure slower than the "
                   "same arithmetic fused even at 64x64, so this case cannot "
                   "resolve a joint at any size and reports nothing")

    # -- at the analysis form: one edge, against the noise floor
    graph = Graph().add(blur_node()).add(diff_node())
    one = timed(lambda r: fused_diff(frames, r), rows)
    again = timed(lambda r: fused_diff(frames, r), rows)
    many = timed(lambda r: evaluate_recompute(graph, "diff", r, frames), rows)
    a, b = quantiles(one)["p50"], quantiles(many)["p50"]
    floor = abs(quantiles(again)["p50"] - a)
    overhead = b - a

    run.note(f"joints: {per_edge * 1000:.1f} us per edge, from a {edges}-edge "
             "chain over a 64x64 array, where the work is small enough for a "
             "joint to resolve")
    run.note(f"joints at the analysis form: fused {a:.3f} ms/position, staged "
             f"{b:.3f} ms, difference {overhead:+.3f} ms against a noise floor "
             f"of {floor:.3f} ms — "
             + ("resolvable" if abs(overhead) > floor else
                f"below the floor, so one edge over a {form.out[0]}x"
                f"{form.out[1]} gray form costs less than this instrument can "
                "see"))
    # The two figures are not one figure at two sizes, and reading them as one
    # was this file's second mistake: 0.2 us at 64x64 multiplied by a ten-edge
    # graph says joints are free, which is only true at 64x64. They scale with
    # the array, because what an edge really costs is materialising an
    # intermediate somebody fused would never have named — dispatch is the
    # small half.
    scaling = overhead / per_edge if per_edge > 0 else float("nan")
    run.note(
        f"joints, read: {per_edge * 1000:.1f} us an edge at 64x64 and "
        f"{overhead * 1000:.0f} us at the analysis form — {scaling:.0f}x for "
        f"{(form.out[0] * form.out[1]) / (64 * 64):.0f}x the pixels, so an "
        "edge costs the intermediate it names and not the call that names it. "
        f"At the analysis form a ten-edge graph spends about "
        f"{10 * overhead:.2f} ms on joints, which is "
        f"{100 * 10 * overhead / 33.37:.0f}% of a 30 fps period. Generality is "
        "affordable; it is not free, and it is priced in bytes touched.")
    keep(run, "joints-fused-small", flat, edges=0, array="64x64")
    keep(run, "joints-staged-small", deep, edges=edges, array="64x64")
    keep(run, "joints-fused", one, edges=0, array=form.key())
    keep(run, "joints-fused-repeat", again, edges=0, array=form.key(),
         note="the noise floor: the same work measured twice")
    keep(run, "joints-staged", many, edges=1, array=form.key())
    return "joints (what an edge costs)", 3, bad


def case_reuse(run: Run, frames, form) -> tuple[str, int, list[str]]:
    """G5: recompute against store, at two declared reuse factors."""
    bad: list[str] = []
    rows = list(range(BASE_ROW, BASE_ROW + POSITIONS))
    told = []
    for label, sink, node in (("diff", "diff", diff_node()),
                              ("mhi", "mhi", mhi_node())):
        graph = Graph().add(blur_node()).add(node)
        reuse = len(node.offsets)
        again = timed(lambda r, g=graph, s=sink:
                      evaluate_recompute(g, s, r, frames), rows)
        kept: dict[tuple[str, int], np.ndarray] = {}
        once = timed(lambda r, g=graph, s=sink:
                     evaluate_stored(g, s, r, frames, kept), rows)
        slow, fast = quantiles(again)["p50"], quantiles(once)["p50"]
        held = len(kept) * form.nbytes
        if fast > slow:
            bad.append(f"{label}: keeping the intermediate ({fast:.3f} ms) "
                       f"cost more than recomputing it ({slow:.3f} ms) at a "
                       f"declared reuse of {reuse}")
        told.append((label, reuse, slow, fast, held, len(kept)))
        keep(run, f"reuse-{label}-recompute", again, reuse=reuse,
             policy="recompute")
        keep(run, f"reuse-{label}-keep", once, reuse=reuse, policy="keep",
             held_bytes=held, held_arrays=len(kept))
        run.note(f"reuse[{label}]: reuse {reuse}, recompute {slow:.3f} ms/"
                 f"position, keep {fast:.3f} ms, holding {len(kept)} "
                 f"intermediates ({held / 1e6:.1f} MB)")
    # Whether the saving tracks the declaration is reported and not asserted.
    # It is the thing a scheduler would want to predict from a declaration, and
    # if it does not track, that is a result about what can be predicted rather
    # than a case that has broken.
    two, four = told[0], told[1]
    saved_two, saved_four = two[2] - two[3], four[2] - four[3]
    run.note(
        f"reuse, read: a declared reuse of {two[1]} saved {saved_two:.3f} "
        f"ms/position and a declared reuse of {four[1]} saved "
        f"{saved_four:.3f} ms — "
        + ("the saving grows with the declared reuse, so a scheduler can "
           "predict from a declaration what keeping an intermediate buys."
           if saved_four > saved_two else
           "the saving does NOT grow with the declared reuse. Keeping costs "
           "memory traffic that grows with what is kept, so a declaration "
           "bounds the saving without predicting it, and a scheduler reading "
           "offsets alone would over-estimate what caching buys."))
    return "reuse (keeping beats recomputing)", 3, bad


def case_crossover(run: Run, frames, form, decode_ms) -> tuple[str, int, list[str]]:
    """G5's other half: what the bytes would have been worth as frames."""
    bad: list[str] = []
    rows = list(range(BASE_ROW, BASE_ROW + POSITIONS))
    node = mhi_node()
    graph = Graph().add(blur_node()).add(node)
    again = timed(lambda r: evaluate_recompute(graph, "mhi", r, frames),
                  rows)
    kept: dict[tuple[str, int], np.ndarray] = {}
    once = timed(lambda r: evaluate_stored(graph, "mhi", r, frames, kept),
                 rows)
    saved_ms = quantiles(again)["p50"] - quantiles(once)["p50"]
    frames_forgone = len(kept)          # one intermediate is one frame of room
    if saved_ms <= 0:
        bad.append("keeping saved nothing, so there is no trade to price")
        return "crossover (bytes as frames)", 2, bad

    # Spending the same bytes on frames avoids a decode each time one of those
    # rows is wanted again. Break-even is where the compute saved per position
    # equals the decode avoided per position.
    positions = len(again)
    saved_total = saved_ms * positions
    decode_total = decode_ms * frames_forgone
    verdict = ("keeping the intermediate" if saved_total > decode_total
               else "spending the bytes on frames")
    ratio = saved_total / max(decode_total, 1e-9)
    # The actionable number: the decode cost at which the two are equal. Below
    # it, room is cheap and keeping the intermediate wins; above it, room is
    # what prevents decodes and the bytes are worth more as frames.
    break_even = saved_total / max(frames_forgone, 1)
    run.note(
        f"crossover: over {positions} positions keeping saved "
        f"{saved_total:.0f} ms while the same {frames_forgone} arrays' worth "
        f"of room would have avoided {decode_total:.0f} ms of decode at this "
        f"machine's {decode_ms:.2f} ms/frame — {ratio:.2f}x, so {verdict} wins "
        "here.")
    run.note(
        f"crossover break-even: {break_even:.2f} ms per frame. A fetch dearer "
        "than that makes the room worth more as frames; a fetch cheaper than "
        "that makes the intermediate worth keeping. The verdict is not the "
        "result — the threshold is, because a session reads frames from a "
        "decode, a chunk and a proxy at costs that straddle it.")
    run.note(
        "crossover, how far to trust it: the threshold is a ratio of two "
        "timings and moves by more between runs than either does within one, "
        "so it is an order-of-magnitude claim and not a figure to branch on. "
        "What it is being read for is which side of it the tiers sit, and "
        "successive runs in results/ are where a later one supersedes this.")
    keep(run, "crossover-recompute", again, node="mhi", policy="recompute")
    keep(run, "crossover-keep", once, node="mhi", policy="keep",
         held_arrays=frames_forgone, break_even_ms_per_frame=break_even)
    return "crossover (bytes as frames)", 2, bad


def case_key(run: Run, frames, keyer) -> tuple[str, int, list[str]]:
    """G6: two graphs differing only upstream, and what tells them apart."""
    bad: list[str] = []
    rows = list(range(BASE_ROW, BASE_ROW + 12))
    store: dict[str, dict[int, float]] = {}
    truth: dict[str, dict[int, float]] = {}

    for k in (3, 11):
        graph = Graph().add(blur_node(k)).add(diff_node())
        key = keyer(graph, "diff")
        into = store.setdefault(key, {})
        mine = truth.setdefault(str(k), {})
        for row in rows:
            value = float(np.mean(evaluate_recompute(graph, "diff", row,
                                                     frames)))
            mine[row] = value
            into.setdefault(row, value)     # first writer wins, as a cache does

    if len(store) != 2:
        bad.append(f"two graphs that differ upstream were filed under "
                   f"{len(store)} key(s); one is reading the other's numbers")
    # And the numbers must actually differ, or the case proves nothing.
    a, b = truth["3"], truth["11"]
    if all(abs(a[r] - b[r]) < 1e-9 for r in rows):
        bad.append("the two blurs produced identical numbers, so this case "
                   "could not tell a shared key from a correct one")
    for k, mine in (("3", a), ("11", b)):
        graph = Graph().add(blur_node(int(k))).add(diff_node())
        filed = store[keyer(graph, "diff")]
        wrong = [r for r in rows if abs(filed[r] - mine[r]) > 1e-9]
        if wrong:
            bad.append(f"blur k={k}: {len(wrong)} of {len(rows)} values read "
                       "back under its key were computed by a different graph")
    run.note(f"key: two graphs differing only upstream filed under "
             f"{len(store)} key(s); values differ by "
             f"{max(abs(a[r] - b[r]) for r in rows):.4f} at most")
    return "key (upstream reaches the name)", 3, bad


def main() -> None:
    broken = "--broken" in sys.argv
    keyer = local_only_key if broken else subgraph_key

    run = Run(
        experiment="G3G5G6-joints-and-reuse" + ("-broken" if broken else ""),
        question="What do the joints cost, what is reuse worth, and what "
                 "keeps two graphs apart?",
    )
    run.add_footage(BIG)
    run.note("ISOLATED: resident frames, one thread, no store, no fill, no "
             "drawing. Right instrument for arithmetic against arithmetic and "
             "the wrong one for anything felt. Not to be quoted as a loop cost.")
    if broken:
        run.note("RUN WITH --broken: the key folds only the sink's own params, "
                 "which is what the tool explorer's blur chaining does. `key` "
                 "is expected to FAIL.")

    frames, form, decode_ms = decode_window(run)
    if len(frames) < ROWS - 5:
        run.note(f"only {len(frames)} rows decoded; cases run over what there "
                 "is")

    results = [
        case_joints(run, frames, form),
        case_reuse(run, frames, form),
        case_crossover(run, frames, form, decode_ms),
        case_key(run, frames, keyer),
    ]

    ok = True
    print(f"\n{'case':<52} {'checked':>9}  verdict")
    for label, checked, bad in results:
        ok = ok and not bad
        print(f"{label:<52} {checked:>9}  "
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
