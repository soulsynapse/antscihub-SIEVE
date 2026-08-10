---
title: An unconsumed member is named in a list, not left to a check that cannot see it
adr: 36
position: "01.04.02"
status: settled
decided: 2026-08-09
---

A vocabulary admits a member nothing consumes only by naming it in an unconsumed
set beside it. A test refuses both: an unnamed member with no consumer, and a
named member that gained one.

The set sits beside the vocabulary and not in the test that holds it, because
the reader who needs to know which members reach nothing is the one arriving at
the declaration. It only shrinks, and shrinking it belongs to the commit that
lands the consumer rather than to a later tidy — which is the whole of what
makes the deferral loud.

This narrows [ADR 8](declared-means-verified.md)'s licensed early admission
rather than replacing it. That license let a declaration whose consumer is
scheduled by the plan stand on a registration-time validity check — a closed
vocabulary, refusal by name — "standing in as the consumer until the real one
lands". Refusal by name proves a member is spelled correctly and says nothing
about whether anything consumes it, so it is green the moment the member is
minted and stays green however long the consumer takes; nothing in it can go red
when the real consumer lands beside a stand-in that stays. Both halves are now
required of an early admission: the check, and the name in the set.

Why: the construction is already in this repo three times, reached separately by
work that was not sharing a rule — `bench/budgets.py`'s `WITHOUT_PRODUCER`, with
`tests/bench/test_budget_producers.py` holding both directions;
`mutual/shares.py`'s `UNBOUNDED`, whose own comment names the first as its
source; and that module's `SENSED`/`WITHOUT_SENSOR` pair, which
`tests/unit/test_ledger_sensors.py` holds to exactly the rows that exist, so a
new one lands in one list or the other in the commit that creates it. Three
sites converging on one shape is where it stops being each site's trick.

What it costs when the rule is absent is
[a declared surface drawn by nothing](../todo/a-declared-surface-is-drawn-by-nothing.md):
a stereotype admitted under the old license, carried past two generators that
each deferred its editor, with the tree green throughout because everything able
to go red was about spelling. The general form is
[a loud deferral covers for a silent one](../findings/loop/2026.08.09-a-loud-deferral-covers-for-a-silent-one-in-the-same-sentence.md)
— a gap named once in prose and nowhere in the tree.

What this does not claim: that a listed member is unreachable, or that an
unlisted one is truly wired. The check is a reference and not a call-graph
proof, deliberately, for the reason `test_budget_producers.py` gives about its
own scanners — the weaker claim is stable against how a module names its member
and still catches the failure that matters. Its scope is declaration
vocabularies read by machinery, not every unused symbol; a member one reader
consumes is consumed.

Admissions already made under the old license are not reopened by this. What
they owe is the set, and the first commit under this rule is where each
vocabulary's gaps stop being prose.
