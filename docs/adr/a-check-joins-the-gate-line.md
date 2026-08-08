---
title: What earns a place on the gate line
adr: 20
position: "03.05"
status: settled
decided: 2026-08-07
---

A check joins the gate line when it is cheap against the line's cost, no other
placement catches what it catches, and scoping it to its files would enumerate
the gate's membership twice.

All three, argued in the commit that adds it; the third clause is
[ADR 19](the-gate-is-one-line.md)'s. A check that fails the first belongs
somewhere else, and one that fails the second has no somewhere else to be.
Why: `actionlint` is the member that shows the rule has teeth. It cannot
fail on a commit that leaves `.github/` alone, and it is on the line anyway,
because a step inside `ci.yml` is not the same check one push later — the
errors worth catching there are the ones that stop the job, so that step never
runs — and a `paths:` entry only ever narrows CI, which leaves the laptop run
untouched, and the laptop run is where the whole class of error is first
catchable
(`findings/2026.08.07-actionlint-is-seven-tenths-of-a-percent-of-the-gate.md`).
`ruff format --check` entered on the same three clauses.

Cheap is deliberately not a number. That finding priced actionlint at 0.7% of
the gate and judged that two seconds would have bought a `paths:` entry its
second list; a threshold picked between those would be invented rather than
measured, so the comparison stays against whatever the line costs at the time
and is re-argued per check.

Two rules rather than one, because these are peers: membership cites
no-second-copy in its third clause and nowhere else, and the two have already
been read as each other — "one command, not two lists" is a claim about copies
of the line, and has been cited as a claim about what belongs on it.
