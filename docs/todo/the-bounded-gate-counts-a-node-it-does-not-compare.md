---
title: The BOUNDED gate counts a node nothing compares
priority: normal
phase: 8
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_cache_admission.py -k every_bounded_tool_is_compared -q"
opened: 2026-08-09
---

# The BOUNDED gate counts a node nothing compares

`test_every_bounded_tool_is_covered_by_a_served_case` in
`tests/unit/test_cache_admission.py` derives its covered set from
`plan.dag.order` — every node the executor was handed — and its required set
from the `BOUNDED` specs `discover()` returns. That is coverage by *membership
in a graph*. What the ADR admits a tool on is coverage by *comparison*: served
equals cold, exactly. Those two are the same set today and by accident — both
`ServedCase` graphs hold exactly two nodes, and the parity assertions that
carry the ADR's claim iterate literal tuples, `(BLOCKS, DETECTOR)` in
`test_a_bounded_warmup_tool_served_from_the_store_equals_its_cold_run` and
`(BLOCKS, NORMALIZED)` in `test_an_entry_is_never_a_lead_in_frames_under_warmed_output`.

So the third tool the gate exists for satisfies it by being added as a node and
nothing more. Its author reads a failure message that says to put the tool in a
graph a `ServedCase` compares, adds the node, goes green, and no assertion
anywhere has compared their tool's served output to its cold one — the same
hand-written list the gate was minted to remove, one level down, now deciding
what is checked rather than what is required. A leaf with no downstream
consumer is the worst case: a divergence in it propagates nowhere, so even the
existing comparisons cannot catch it by accident.

What should be different: coverage and comparison are one fact. The gate
already holds `served` and `cold` from every case it runs and throws them away
after an emptiness check; asserting `np.array_equal` per node over
`plan.dag.order` there makes the covered set true by construction, and the two
literal tuples above become derivations of the same walk or go away. Renaming
the gate to `test_every_bounded_tool_is_compared_served_against_cold` is what
makes the criterion red today — it is green under the old name and would
certify work nobody did.

Whether the per-node dtype assertion and the served-prefix assertions
(`test_the_served_range_stops_inside_the_span_and_both_tools_carry_on`) also
derive is open; that one is about which frames were served and not about
equality, and a node with no cache policy at all would have to be excluded
rather than asserted over.

The sequence above happened, on the day this was opened and by an author who
had not read it. A fourth `BOUNDED` tool — a dense-flow node on a scratch
branch — went red at the gate, its author read the failure message, added a
`farneback -> normalize` graph and a third `ServedCase`, and went green in one
edit. Nothing compared either node: both parity assertions iterate their
literal tuples, and neither names the two node ids the new graph introduced.
The prediction needed no help and no adversary to come true, which is the
argument for the fix above rather than for a better failure message.

That leaves a second question this did not ask: whether the *cases* derive too,
and not only the comparison. Deriving the comparison closes the correctness
hole on its own — a hand-built graph whose nodes are all compared is honest —
and what stays open under it is the shape, a shared file every `BOUNDED` tool
after this one has to enter with a graph of its own, which is
`adr/a-tool-is-one-file.md`'s subject read as a cost curve. The obstacle is why
the graphs are hand-built at all: the three `BOUNDED` tools accept disjoint
inputs — `block_signal` takes four dtypes, `detect` float32 GRAY alone,
`farneback` uint8 alone — so no single source feeds them. `Footage` in
`tests/unit/test_declarations_run.py` already solves exactly that, deriving
frames from a spec's own `accepts` and running every tool on the shelf as a
lone root with `detect` among them, so a `ServedCase` carrying a source beside
its pipeline could be minted per `BOUNDED` spec and the hand-built graphs would
stay only for the claims a lone root cannot make — the served-to-computed
transition inside the span, and the node with no warmup beneath one that has
some. What that costs is a home for `Footage` both files can read, and
`tests/conftest.py` is not it: that module never imports `sieve`, by an argument
in its own docstring, and a helper taking a `ToolSpec` cannot honour it.
