"""G4. Does a graph still have a fetch plan, and can anything hold it?

The product constraint is not that graphs are fast. It is that they refill
faster than the video plays, which is only reachable by *prefetching*, which
needs a plan computable before anything runs (ADR-0006). A graph that can only
say what it needs once it gets there is demand-driven, and no amount of speed
recovers prefetch. So this is the goal that can implicate the architecture
rather than a tool.

Almost all arithmetic, and deliberately so: composition either works on paper or
it does not, and a measurement would only tell us how fast the wrong answer
arrives. No footage. The one empirical-shaped case turns a set of rows into
bytes at a real form and compares it against the budget the session actually
runs with, which is arithmetic over a measured constant rather than a new
measurement.

**How composition is supposed to work.** A node declares offsets relative to
*its own inputs*, not to the source. If B admits `(-1, 0)` of A and A admits
four lags of the source, then B at row r needs source rows `{r + b + a}` for
every pair — the Minkowski sum along the path, unioned over paths when a DAG
has more than one. Nothing about that requires running anything, which is the
whole claim.

The declarations are real. `absdiff` and `dis_flow` admit two adjacent rows;
`lag_mhi` admits four rows spanning thirty, and it is the only tool in this tree
whose admitted set is not its reach — which is exactly the property that makes
composition non-trivial, and the reason it exists as a load.

Six cases.

**line** — a plan computed for a two- and three-node chain matches what a
demand-driven walk of the same graph actually asks for. Plan against actual is
the only honest form of this: an analytic plan that agrees with itself proves
nothing.

**diamond** — two paths reaching one sink union rather than double-counting, and
still match the walk. A line cannot express a mask meeting an image; this is the
smallest graph that can.

**sparse** — what planning by *span* instead of by set costs. A lazy
implementation takes the minimum and maximum of a composed offset set and
fetches the run between them, which is correct and over-fetches. ADR-0008 calls
a fetch nobody needed a bug rather than a price, so the size of that gap is the
size of the bug.

**residency** — the case that answers *can anything hold it*. The point set and
the working set behave differently under composition, and the difference is the
result: the number of distinct offsets multiplies with depth, while what has to
be resident over a moving playhead grows only by the added reach. If that holds,
depth is affordable for a playing loop in a way the point-set arithmetic makes
it look like it is not.

**bytes** — the residency for a realistic graph at a real analysis form, against
`session.BUDGET_BYTES`.

`--broken` computes the plan from the sink node's offsets alone, ignoring
everything upstream. That is not an invented mistake: it is what the tool
explorer does today. `Rig.set_tool` chains a blur ahead of a tool by wrapping
its `field` and folding the blur's parameter into the downstream tool's params,
and only the downstream tool's `offsets` are ever read — so an upstream node
with a reach of its own has that reach silently dropped. It works there because
a Gaussian blur admits one row. `line`, `diamond` and `residency` are expected
to fail under it.

`sparse` and `bytes` still pass under `--broken`, and that is worth reading
rather than tidying away: a plan that under-fetches is *cheaper*, so every case
asking whether the working set is affordable comes out better when the plan is
wrong. Cost instruments cannot see this class of defect, which is the same thing
`tool-experiments` records about the overlay that wrote its own series — four
experiments measuring cost never saw it, and a question about shape did.

Run:
    uv run --group experiments python experiments/chain-experiments/02-offsets-compose.py
    uv run --group experiments python experiments/chain-experiments/02-offsets-compose.py --broken
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field as dc_field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tool-experiments"))
import harness  # noqa: E402
from harness import Run  # noqa: E402

import tools as toolkit  # noqa: E402  the real declarations
from sieve.frame.form import Form  # noqa: E402
from sieve.session.session import BUDGET_BYTES, WINDOW_ROWS  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

#: the name reserved for the root. A node listing this as an input is reading
#: decoded frames rather than another node's output.
SOURCE = "source"

#: how far ahead of the playhead a fill works. The horizon `residency` is asked
#: over, and the reason the point set and the working set diverge.
AHEAD = WINDOW_ROWS


@dataclass(frozen=True)
class Node:
    """One node's declaration: what it reads, and at what offsets from it."""

    name: str
    offsets: tuple[int, ...]
    inputs: tuple[str, ...] = (SOURCE,)


@dataclass
class Graph:
    nodes: dict[str, Node] = dc_field(default_factory=dict)

    def add(self, node: Node) -> "Graph":
        self.nodes[node.name] = node
        return self

    def depth(self, name: str) -> int:
        node = self.nodes[name]
        ups = [self.depth(i) for i in node.inputs if i != SOURCE]
        return 1 + (max(ups) if ups else 0)


# ── the plan, computed ───────────────────────────────────────────────────────
def offsets_to_source(graph: Graph, name: str) -> frozenset[int]:
    """Every offset from the evaluated row that reaches the source.

    The Minkowski sum along each path, unioned over paths. A node reading the
    source contributes its own offsets; a node reading another contributes its
    offsets added to everything that one already reaches.
    """
    node = graph.nodes[name]
    out: set[int] = set()
    for upstream in node.inputs:
        below = (frozenset({0}) if upstream == SOURCE
                 else offsets_to_source(graph, upstream))
        out |= {mine + theirs for mine in node.offsets for theirs in below}
    return frozenset(out)


def plan(graph: Graph, sink: str, row: int) -> frozenset[int]:
    """The source rows needed to evaluate `sink` at `row`, before running."""
    return frozenset(row + off for off in offsets_to_source(graph, sink))


def local_plan(graph: Graph, sink: str, row: int) -> frozenset[int]:
    """The plan from the sink's own offsets, ignoring upstream. The bug."""
    return frozenset(row + off for off in graph.nodes[sink].offsets)


def span_plan(graph: Graph, sink: str, row: int) -> frozenset[int]:
    """Everything between the furthest and nearest offset. Correct, and fat."""
    reach = offsets_to_source(graph, sink)
    return frozenset(range(row + min(reach), row + max(reach) + 1))


def plan_residency(graph: Graph, sink: str, rows, planner=None) -> frozenset[int]:
    """What must stay resident to serve a run of positions.

    Takes the planner rather than reaching for `plan`, so that a broken plan
    produces a broken working set. The first version of this called `plan`
    directly and reported a ratio between a correct working set and a broken
    point set, which is a number about nothing.

    The union over the horizon, which is `tools.residency`'s distinction — the
    point set at one position is not the working set of a sequence, and
    honouring the point set for a moving playhead costs a fetch per offset per
    position (ADR-0006).
    """
    planner = planner or plan
    out: set[int] = set()
    for row in rows:
        out |= planner(graph, sink, row)
    return frozenset(out)


# ── what a graph actually asks for, by running it ────────────────────────────
def walk(graph: Graph, sink: str, row: int, asked: set[int] | None = None):
    """Evaluate demand-driven, recording every source row touched.

    No pixels. What is being compared is which rows a demand-driven evaluation
    reaches against which rows the plan named, and an array would only make the
    comparison slower. A node asks its inputs for `row + offset` and they ask
    theirs, exactly as a graph with no plan would have to.
    """
    if asked is None:
        asked = set()
    node = graph.nodes[sink]
    for off in node.offsets:
        for upstream in node.inputs:
            if upstream == SOURCE:
                asked.add(row + off)
            else:
                walk(graph, upstream, row + off, asked)
    return asked


# ── the graphs, from real declarations ───────────────────────────────────────
def declarations() -> dict[str, tuple[int, ...]]:
    """Offsets taken off the tools themselves rather than written out here.

    Restating them would make this file agree with a copy of the tools instead
    of with the tools, which is the failure the crop clamp already paid for
    once.
    """
    return {
        "absdiff": toolkit.absdiff().offsets,
        "dis": toolkit.dis_flow().offsets,
        "mhi": toolkit.lag_mhi().offsets,
    }


def line_graph(decl) -> Graph:
    """source → mhi → absdiff. The sparse node upstream, where it is worst."""
    return (Graph()
            .add(Node("mhi", decl["mhi"]))
            .add(Node("diff", decl["absdiff"], inputs=("mhi",))))


def deep_graph(decl) -> Graph:
    """Three deep, with the sparse node in the middle."""
    return (Graph()
            .add(Node("diff", decl["absdiff"]))
            .add(Node("mhi", decl["mhi"], inputs=("diff",)))
            .add(Node("flow", decl["dis"], inputs=("mhi",))))


def diamond_graph(decl) -> Graph:
    """Two paths to one sink — the shape a line cannot express."""
    return (Graph()
            .add(Node("diff", decl["absdiff"]))
            .add(Node("mhi", decl["mhi"]))
            .add(Node("join", (0,), inputs=("diff", "mhi"))))


# ── cases ────────────────────────────────────────────────────────────────────
def case_line(run: Run, planner) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    decl = declarations()
    checked = 0
    for label, graph, sink in (("two-deep", line_graph(decl), "diff"),
                               ("three-deep", deep_graph(decl), "flow")):
        for row in (500, 1000):
            want = planner(graph, sink, row)
            got = frozenset(walk(graph, sink, row))
            checked += 1
            if want != got:
                short = sorted(got - want)[:6]
                over = sorted(want - got)[:6]
                bad.append(
                    f"{label} at {row}: the plan named {len(want)} rows and the "
                    f"walk asked for {len(got)}; missed {short}, "
                    f"over-fetched {over}")
    run.note(f"line: two- and three-deep chains, plan against walk, "
             f"{checked} positions")
    return "line (plan == what it asks for)", checked, bad


def case_diamond(run: Run, planner) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    decl = declarations()
    graph = diamond_graph(decl)
    want = planner(graph, "join", 800)
    got = frozenset(walk(graph, "join", 800))
    if want != got:
        bad.append(f"diamond: planned {len(want)} rows, walked {len(got)}")
    # The union must not be the sum: the two paths overlap at row 800 and the
    # near lags, and a plan that added them would over-fetch by the overlap.
    both = (frozenset(decl["absdiff"]) & frozenset(decl["mhi"]))
    if both and len(want) >= len(decl["absdiff"]) + len(decl["mhi"]):
        bad.append(f"the two paths share {len(both)} offsets and the plan "
                   "counted them twice")
    run.note(f"diamond: two paths to one sink plan {len(want)} rows, "
             f"sharing {len(both)} offsets")
    return "diamond (paths union, not sum)", 2, bad


def case_sparse(run: Run, planner) -> tuple[str, int, list[str]]:
    """What planning by span instead of by set costs, at depth."""
    bad: list[str] = []
    decl = declarations()
    graph = deep_graph(decl)
    tight = planner(graph, "flow", 1000)
    fat = span_plan(graph, "flow", 1000)
    if not tight <= fat:
        bad.append("the tight plan is not contained in the span plan, so one "
                   "of the two is wrong rather than merely fatter")
    waste = len(fat) - len(tight)
    if waste <= 0:
        bad.append("planning by span cost nothing at depth three, which would "
                   "mean the composed set is dense and this case is not "
                   "exercising sparse admission at all")
    run.note(f"sparse: three-deep, a set plan wants {len(tight)} rows and a "
             f"span plan {len(fat)} — {waste} fetched and unused, which "
             "ADR-0008 calls a bug rather than a price")
    return "sparse (set beats span, measurably)", 2, bad


def case_residency(run: Run, planner) -> tuple[str, int, list[str]]:
    """Does the working set grow with depth the way the point set does?"""
    bad: list[str] = []
    decl = declarations()
    rows = range(1000, 1000 + AHEAD)
    shapes = [("one", Graph().add(Node("mhi", decl["mhi"])), "mhi"),
              ("two", line_graph(decl), "diff"),
              ("three", deep_graph(decl), "flow")]
    points, held, spans = [], [], []
    for _label, graph, sink in shapes:
        points.append(len(planner(graph, sink, 1000)))
        resident = plan_residency(graph, sink, rows, planner)
        held.append(len(resident))
        spans.append(max(resident) - min(resident) + 1)

    # The claim: the point set multiplies with depth, the working set does not.
    if not points[2] > points[0]:
        bad.append("the point set did not grow with depth, so this graph is "
                   "not exercising composition")
    growth_point = points[2] / points[0]
    growth_held = held[2] / held[0]
    if growth_held >= growth_point:
        bad.append(
            f"the working set grew by {growth_held:.2f}x against the point "
            f"set's {growth_point:.2f}x — composition is reaching memory, and "
            "the needs/residency distinction does not survive depth")
    # And it should be bounded by the horizon plus the reach, not by the set.
    for (label, graph, sink), n in zip(shapes, held):
        reach = -min(offsets_to_source(graph, sink))
        bound = AHEAD + reach
        if n > bound:
            bad.append(f"{label}: {n} rows resident over a horizon of {AHEAD} "
                       f"with a reach of {reach}, past the {bound} bound")
    run.note(
        f"residency: over a {AHEAD}-row horizon the point set goes "
        f"{points} and the working set goes {held}, spanning {spans}")
    return "residency (depth adds reach, not multiples)", 4, bad


def case_bytes(run: Run, planner) -> tuple[str, int, list[str]]:
    """The working set in bytes, at a real form, against the real budget."""
    bad: list[str] = []
    decl = declarations()
    graph = deep_graph(decl)
    # A crop a person might actually draw, at source sampling in gray, which
    # is what `analysis_form` gives a step.
    form = toolkit.analysis_form("gray")((0, 0, 1920, 1080))
    resident = plan_residency(graph, "flow", range(1000, 1000 + AHEAD),
                              planner)
    total = len(resident) * form.nbytes
    if total > BUDGET_BYTES:
        bad.append(f"a three-deep graph over a {AHEAD}-row horizon wants "
                   f"{total / 1e9:.2f} GB resident against a budget of "
                   f"{BUDGET_BYTES / 1e9:.2f} GB")
    run.note(f"bytes: {len(resident)} rows at {form.key()} is "
             f"{total / 1e9:.3f} GB, {100 * total / BUDGET_BYTES:.0f}% of "
             "the session budget")
    return "bytes (the working set fits)", 1, bad


def main() -> None:
    broken = "--broken" in sys.argv
    planner = local_plan if broken else plan

    run = Run(
        experiment="G4-offsets-compose" + ("-broken" if broken else ""),
        question="Does a graph still have a fetch plan, and can anything hold "
                 "it?",
    )
    run.note("arithmetic, no footage: composition either works on paper or it "
             "does not")
    run.note(f"offsets taken off the tools themselves: {declarations()}")
    if broken:
        run.note("RUN WITH --broken: the plan is computed from the sink's own "
                 "offsets alone, which is what `Rig.set_tool` does today when "
                 "it chains a blur. `line`, `diamond` and `residency` are "
                 "expected to FAIL.")

    results = [
        case_line(run, planner),
        case_diamond(run, planner),
        case_sparse(run, planner),
        case_residency(run, planner),
        case_bytes(run, planner),
    ]

    ok = True
    print(f"{'case':<46} {'checked':>9}  verdict")
    for label, checked, bad in results:
        ok = ok and not bad
        print(f"{label:<46} {checked:>9}  "
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
