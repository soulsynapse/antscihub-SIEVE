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

## Worker note, 2026-08-07

Struck. 00.3's `done_when` is now
`uv run pytest tests/unit/test_gate_line.py -q && uv run actionlint`: the check
that reads the gate line off `ci.yml`, and the one command whose subject is the
workflow's own validity, which is the part of the old line the item's content
turned on. Its opening paragraph no longer enumerates anything, which is where
the third drift was.

Striking rather than pinning, because pinning is the reading ADR 19 refuses one
paragraph later for a `paths:` entry: two enumerations and a mechanism to keep
them in step is worse than one enumeration, and the mechanism only ever tells
you the second copy is wrong. Nothing was lost that a person runs — a
contributor pushing reads `ci.yml`, which ADR 19 already says is the one place
to read.

The walk is `test_no_restatement_of_the_gate_line_drifts_from_it`, and what it
calls a restatement is a `done_when` whose commands are a prefix of the gate
line's or a superset with the line as its prefix. The prefix half is the one
that carries weight: the `actionlint` drift was the line minus its newest
command, so a rule that only caught an equal-length copy would be blind to the
shape that failure took. Checked by simulation before striking — restoring the
four-command copy that stood from `e9d1db4` to `2e64785` turns the walk red and
names both lines. Two
neighbours stay out and should: `the-gate-has-no-opinion-about-the-workflow.md`
is checked by three gate commands that were never the line (they skip
`ruff format --check`), and `mutual-comes-over-with-its-layer.md` by two in the
wrong order. Neither is a copy of anything; sharing commands with the gate is
what most criteria in the folder do.

Grandfathering was not taken, and the criterion's argument for foreclosing it
holds up: something did require this copy to stay identical — 00.3's own
sentence that the two lines are character-identical — and two reviewers acted
on that requirement. Striking removes the requirement instead of exempting it,
so ADR 19's clause is left saying exactly what it said.

ADR 19 gains two sentences rather than an amendment: its account of the copy
moves to the past tense, because the copy is gone and a settled ADR that
describes the tree as it no longer is decays into the thing it was written
against. The clause itself is untouched.

## Review, 2026-08-07

Reopened. The criterion passes and the strike is the right call, but the walk
is green on one of the two drifts this item's opening paragraph names. Measured
in
`docs/findings/2026.08.07-the-gate-line-walk-catches-one-of-the-two-drifts-the-item-cites.md`:
the `actionlint` episode left the copy as the line's prefix and the walk is red
on it; the `ruff format --check` episode left a hole in the middle and the walk
is silent. The worker note's "both recorded drifts were the line minus its
newest command" is false for the first of them, and the commit it cites for its
red-before-green, `ae6e499`, is the repair rather than the drift — the copy
there is five commands and in step, and the four-command copy is
`e9d1db4`..`2e64785`.

What this item is short of is either a rule that reaches the interior-omission
shape or a stated argument for why it cannot. The second is live:
`the-gate-has-no-opinion-about-the-workflow.md`'s `done_when` is byte-identical
to the first drift's copy and is not a copy of anything, so no rule reading only
the string separates them, and the alternative is a marker in front matter
saying an item's `done_when` is meant to be the line. That marker is a decision,
not a criterion — see the finding's open question. A run that concludes the
narrow rule is the best available says so in the worker note, corrects the two
false sentences, and leaves the walk as it is.

## Worker note, 2026-08-07, after review

The narrow rule is the best available to a walk, and the reason is not that a
wider one is unattractive — it is that the strings do not carry the
distinction. Episode 1's copy, at `a7efe4b`, is
`uv run ruff check . && uv run lint-imports && uv run pytest -q`, and that is
`the-gate-has-no-opinion-about-the-workflow.md`'s `done_when` byte for byte.
One is the forbidden copy of the line and the other restates nothing, so any
rule reading only a `done_when` must return the same verdict for both and one
of the two verdicts is wrong. Length thresholds do not separate them either;
they are the same three commands. That is not a gap to be closed by a cleverer
predicate — it is a proof that a content-shape rule reaching episode 1 does not
exist.

What does carry the distinction is the requirement itself: 00.3's body said the
`done_when` was the gate line, and this item's body says nothing of the kind.
The two candidates for reading that are a walk that greps item prose for the
claim, and a front-matter marker. The first is the same guess one level up,
matching sentences instead of commands, and it goes stale the way the prose it
reads does. The second is the finding's open question and Kendrick's to answer:
a boolean is a second enumeration in ADR 19's sense, and the argument for it is
that a boolean cannot fall a command behind, which is a different failure mode
from the one the clause was written against. That argument is worth making and
it is not a worker's to settle, so nothing here presumes it.

Corrected rather than argued: the note above said both drifts were the line
minus its newest command, which is false of `ruff format --check` — it joined
the line second and left the copy a hole in the middle — and it cited
`ae6e499` for the four-command copy, which is the commit that repaired it; the
copy stood from `e9d1db4` to `2e64785`. The same false sentence was in
`_restates_the_gate_line`'s docstring and in the companion test's, and both now
say which drift the shape is and why the other is unreachable. ADR 19's "each
time for exactly one commit" is corrected to one and three, and its claim that
the walk stands where the reviewer stood is narrowed to the shape it reaches,
citing the finding for which that is.

The walk is unchanged. Verified with the criterion's own command and by
replaying episode 1 as the finding did: still green, still for the reason the
finding gives.
