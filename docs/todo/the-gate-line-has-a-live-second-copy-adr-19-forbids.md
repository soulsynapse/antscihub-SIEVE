---
title: The gate line has a live second copy, and ADR 19 names it without ruling on it
priority: normal
status: open
gated_on: nothing
done_when: "uv run pytest \"tests/unit/test_gate_line.py::test_no_restatement_of_the_gate_line_drifts_from_it\" -q"
phase: "00"
opened: 2026-08-07
---

# The gate line has a live second copy, and ADR 19 names it without ruling on it

[ADR 19](../adr/the-gate-is-one-line.md) settles that the gate is one
`&&`-joined command written once, and that a copy becomes a forbidden one
"exactly when something requires it to stay identical to the line". By that
clause `docs/todo/ci-runs-what-a-commit-must-pass.md`'s `done_when` is one: it
holds the line character-for-character, and it has been brought back into step
by hand twice, once per command added — `ruff format --check` and then
`actionlint`, the second time at `ae6e499`, whose own review note says nothing
compares the two lines so they agree only because a reviewer noticed. The ADR
cites that history as the evidence its rule rests on and then does not say what
becomes of the copy that produced it.

The prose beside that `done_when` has already drifted a third time and is
drifted now: 00.3's body reads "running exactly the `done_when` line — the
linter, the formatter, import-linter, pytest", four commands against a
`done_when` that holds five.

Three ways out, and which one is the decision: strike the copy, so 00.3's
`done_when` names the criterion rather than restates the line and the item's
body stops enumerating it; grandfather it, so ADR 19 says a completed item's
`done_when` is a dated record like a worker note and drift in it is not the
failure the rule is about; or keep it and pin it, so a test compares 00.3's
`done_when` to `ci.yml`'s `run:` line and the second copy is one the tree
maintains rather than a reviewer. The third is the only one that leaves two
enumerations standing, which is what ADR 19 refuses in a `paths:` entry for the
same reason — so it needs the argument the other two do not.

Not urgent: the two lines agree today, which the gate run at `8bfb2e7`
confirms. What is not sound is a settled rule whose one worked example is a
standing exception to it.

## Criterion, written at specify 2026-08-07

The named test walks the items for a `done_when` that restates the gate line
and asserts each one it finds is character-identical to `ci.yml`'s `run:`. It
is silent about which of the first two ways out the run takes, because that is
what the item says to decide: strike the copy and the walk finds nothing and
passes; keep it and pin it and the walk finds one and compares it. Either way
the sentence the test carries is the one the item is short of — that whether
the two agree stops being a thing a reviewer notices.

It forecloses the third way, grandfathering, and that is deliberate rather than
neutral. Grandfathering is not a criterion a session satisfies; it is an
amendment to ADR 19's own clause, which as written makes this copy a live one —
something does require it to stay identical to the line, and two reviews acted
on that requirement. Superseding a decision minted the day before, to exempt
the example it rests on, is a move that gets argued in a worker note and
adjudicated at review, not one a passing command can stand for. A run that
concludes grandfathering is right says so and leaves the criterion unmet; it is
the default the criterion states, not a gag.

`tests/unit/test_gate_line.py` is the home because the gate line's other five
claims are there and `_gate_line()` already reads the `run:` off the step. Not
`tests/docs/test_doc_index.py`: this is a claim about the gate, and the items
are the place one of its copies happens to live.

The red is the selector's — `ERROR: not found`, `exit 4` — because the test
does not exist. The substantive red is that nothing in the tree reads an item's
`done_when` at all: `grep -rn 'done_when' tests/` returns only
`test_doc_index.py`'s fixtures, which write the field into a temporary item and
never read this repo's. So the two lines agree today by the arrangement the
item names and by nothing else.
