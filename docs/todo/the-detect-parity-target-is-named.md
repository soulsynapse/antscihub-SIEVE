---
title: The detect parity target is named before detect is written
priority: high
phase: 4
status: done
gated_on: nothing
opened: 2026-08-07
---

# The detect parity target is named before detect is written

PLAN.md states the target twice — the Phase 4 gate says v2's `detect/`
package output, centered whole-record, because that is what was tuned
against; the open questions list says confirm it. 04.8's criterion names
three test files and no target, so as written the item can be finished
against either one.

The two are not close: the package composes a centered whole-record pass, the
v2 module of the same name is a trailing kernel, and the whole reason
detection blocked in v2 was that the trailing window could not express what
the detector does. Picking the kernel would reproduce the bug the plan's
lookahead contract (01.3) exists to fix — which is the argument for closing
this rather than leaving it open.

Closing it means: the sentence in PLAN.md loses "confirm", 04.8's `done_when`
gains the artifact it compares against, and the golden's regeneration command
(02.4's mechanism) names the package entry point, not the module.

## Ruled 2026-08-07: the package output, and "confirm" is gone

PLAN.md's Phase 4 gate now states it without hedging and 04.8 carries it in
its body: the golden is minted from `detect/`'s package entry point, and the
regeneration command recorded beside it names that entry point rather than
the module. A run comparing against `filters/detect.py` has taken the wrong
artifact.
