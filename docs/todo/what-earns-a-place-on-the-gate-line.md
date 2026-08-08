---
title: What earns a place on the gate line is argued in three files and settled in none
status: open
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
