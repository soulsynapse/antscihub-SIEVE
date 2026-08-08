---
title: What earns a place on the gate line is argued in three files and settled in none
status: awaiting-review
gated_on: nothing
priority: normal
phase: "00"
done_when: "uv run pytest \"tests/unit/test_gate_line.py::test_the_gate_steps_comment_cites_the_rule_it_applies\" -q"
opened: 2026-08-07
---

# What earns a place on the gate line is argued in three files and settled in none

The gate is one line and the rule for what may join it is now stated three
times: `ci.yml`'s comment says there is no second copy of the line, 00.3
([ci-runs-what-a-commit-must-pass.md](ci-runs-what-a-commit-must-pass.md)) says
the local gate and CI are one command rather than two lists, and
[the-gate-has-no-opinion-about-the-workflow.md](the-gate-has-no-opinion-about-the-workflow.md)
argued the rule again from scratch to place `actionlint` — because none of the
three homes was a place a rule could be cited from. A fourth check will argue
it a fourth time.

The rule that run has to state, and the ADR is where it would bind: a check
joins the gate line when it is cheap against the line's existing cost, when the
alternative placement cannot catch what it catches, and when scoping it to the
files it applies to would be a second enumeration of the gate's membership.
`ruff format --check` and `actionlint` both entered on some version of that
sentence, and `actionlint` is the one that shows it has teeth — it is on the
line despite being unable to fail on most commits, because the two placements
that would have made it conditional either cost a second list or cannot run
(`findings/2026.08.07-actionlint-is-seven-tenths-of-a-percent-of-the-gate.md`).

Whether it is *one* ADR is the part to decide rather than assume. The gate's
membership rule and the one-line/no-second-copy rule are separable claims that
have so far always been argued together, and 00.3's own text is the evidence
that they get confused: "one command, not two lists" is about copies of the
line, not about what belongs on it. The commit that mints this cuts the older
homes to links, per the ADR template.

Not urgent, and deliberately not folded into the commit that placed
`actionlint`: a decision does not ride along inside an implementation, which is
the reason this is a separate item rather than a fifth ADR written by the
session that had the argument fresh.

## Criterion, written at review 2026-08-07

The named test asserts that the gate step's comment in `ci.yml` cites a file
under `docs/adr/` that exists, and it is the checkable half of "settled in one
home": a rule that binds is a rule the place applying it can point at. Today
that comment cites two findings and no ADR — `grep 'adr/\|findings/'` over
`ci.yml` returns only the two `findings/` lines — so the test fails on the
item's own subject rather than on an accident of naming. It is deliberately
silent about how many ADRs there are and where they sit on the shelf, because
that is the part the item says to decide rather than assume; one ADR cited from
the comment satisfies it, and so do two if the run rules that way.

The red pasted at review is the selector's, `exit 4 / ERROR: not found`, since
the test does not exist yet. That red cannot turn green vacuously the way a
`-k` expression matching nothing can — pytest refuses an unknown node id
instead of reporting a pass over zero tests — but it is red for the test's
absence, and the substantive red is the `grep` above.

## Worker note, 2026-08-07

Two ADRs, not one. [ADR 19](../adr/the-gate-is-one-line.md) is the line and
the no-second-copy rule; [ADR 20](../adr/a-check-joins-the-gate-line.md) is
what may join it. `done_when` green:

    1 passed in 0.05s

The whole gate green at the same state, since the commit edits `ci.yml`:
`All checks passed!`, `113 files already formatted`, `Contracts: 6 kept, 0
broken.`, `709 passed in 25.48s`, actionlint silent at exit 0.

### Why two and not one

The test the reviewer wrote is silent about this on purpose, so this is the
part it cannot see. Three arguments were weighed and the third decided it.

Dependence: the membership rule's third clause ("scoping it would be a second
enumeration") is only a cost *because* no-second-copy holds, so membership
cites the other rule. That is a citation, which is what an ADR-to-ADR link is
for, not a merge — one ADR would have been right only if membership could not
be stated without restating no-second-copy, and it can: the first two clauses
stand alone and the third is one link.

Conflation: 00.3's text is the item's own evidence that the two get read as
each other, and a merge is the wrong repair for that. Two numbered files mean
"one command, not two lists" cannot be cited to settle what belongs on the
line, because it is not the file that answers that question.

Supersession, which is what actually decided it. The template's supersede
machinery is per-file. Each rule can move without the other: a repo big enough
to want a `nox` entry point supersedes 19 with 20 intact, and a measured
threshold replacing "cheap against the line's cost" supersedes 20 with 19
intact. One file makes either move rewrite both rules, and the rewrite is where
the conflation would come back.

The reading I rejected, and the strongest one against this: the shelf's grain
is one rule per file *with tightly-bound corollaries folded in* —
`the-product-owns-the-word-tools` carries "`scripts/` is not a package" inside
it. If no-second-copy were a corollary of membership, folding would be right.
It is not: neither rule derives from the other. They are peers that happen to
have always been argued in the same breath, which is exactly the condition
that produced three homes and no binding one.

### What the criterion could not see, and what was checked instead

`done_when` asserts the comment cites an existing ADR. It cannot see whether
the ADR says anything, whether the older homes were cut, or whether the
citation is load-bearing. Checked by hand:

- The test is red on both halves, against `ci.yml` mutated in place and
  restored through bytes: citations replaced by prose gives `assert []` with
  the whole comment in the message, and `adr/the-gate-is-one-lines.md` gives
  the missing-file half. So a green is not the regex matching something
  incidental.
- The comment now cites rather than argues. What was cut: "there is no second
  copy of it in a noxfile or a README" and the whole `actionlint` placement
  paragraph — a step inside `ci.yml` cannot run, a `paths:` entry costs a
  second list, 0.7%. What stayed is file-local and belongs to no ADR: `ruff
  format --check`'s `.` being Python only, grimp not needing an installed
  environment, actionlint taking no path argument.
- The other two homes are links now, not deletions. 00.3's body sentence
  becomes a pointer to ADR 19 — and ADR 19 names that item's own `done_when`
  as the second copy that drifted twice, which is the evidence the rule rests
  on, so cutting it out would have taken the evidence with it.
  `the-gate-has-no-opinion-about-the-workflow.md`'s three-readings paragraph
  is left standing with a pointer appended: it is the question that produced
  ADR 20, and a question is not a second copy of its answer. Neither file's
  dated worker or review notes were touched.

No finding this session. Nothing new was measured — the ADRs rest on
`findings/2026.08.07-actionlint-is-seven-tenths-of-a-percent-of-the-gate.md`,
and the two mutation reds above are the criterion being shown non-vacuous,
which is a worker note's job rather than a finding's.

`filter` is buried by `adr/tools-not-filters.md`, so both ADRs say `paths:`
entry — the same collision
`findings/2026.08.07-the-rename-gate-does-not-survive-borrowed-vocabulary.md`
measured, and the same workaround the run that placed `actionlint` used. Two
sessions in a row have now paid it in a doc.
