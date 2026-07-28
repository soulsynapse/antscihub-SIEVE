---
title: A GUI-saved pipeline must run identically in the CLI
status: open
opened: 2026-07-28

gated_on: >
  nothing — AUTO-GUARDRAILS §2's own trigger ("the next item that touches
  serialization") fired with schema v3 and the check was never written

reads:
  - docs/AUTO-GUARDRAILS.md
  - src/sieve/core/pipeline_model.py
  - src/sieve/pipeline/executor.py
  - src/sieve/cli/run_cmd.py
  - tests/integration/test_cli_run.py
  - src/sieve/gui/document.py
---

# A GUI-saved pipeline must run identically in the CLI

AUTO-GUARDRAILS §2 calls this "the most valuable unwritten check in this file",
and it is right for a reason worth restating: rule 1 says
`pipeline/executor.execute` is the only thing that computes a frame, and
nothing currently tests that. What is tested is that the *layer contract*
makes a second execution path hard to assemble — `gui/` sits above
`pipeline/`, `decode/` is the only route to a frame — which is an argument
about how the code is arranged, not a measurement of what it produces. Rule 1
is a property of the current arrangement rather than a guarantee.

The trigger fired and nobody noticed, which is the other half of why this is
takeable now. Schema v3 landed `Edge.port`, `Project.detector`, and the pin
fields, all serialization, and §2's **Trigger:** line said "the next item that
touches serialization". A trigger nobody polls makes an item a lottery ticket
(see `docs/todo/deferral-expires-by-default.md`).

## What the check is, and what it is not

`tests/integration/test_cli_run.py` builds its projects directly in Python.
That exercises the CLI and the executor; it does not exercise *the artifact
the GUI writes*, which is the only object that can carry a divergence. The
check has to start from a `ReplicateDocument` that has been edited through the
commands — a param edit, a detector edit, a crop — saved with the real writer,
and then run through both front ends with the outputs diffed.

It is a **schema-independent** check, which is the point. A round-trip test
catches a field that fails to serialize. This catches the case where both
sides read the field and one of them resolves it differently — `edited_params`
against the baseline, `None`-means-never-tuned on `DetectorSettings`,
`source_warmup_frames` walking a path the GUI happened to warm differently.
Those are the failures that produce a plausible frame, and a plausible frame
is what rule 6 exists to refuse.

Headless is now available: `docs/completed-todo/2026.07.28-headless-detection.md`
put the detector below both front ends, and `sieve preview --check` is already
an exit code. So the comparison does not need a seated session.

## The thing to not get wrong

Diff the **output**, not the plan. Comparing resolved plans would pass while
both sides compute the same wrong thing, and it would fail on any field that
is legitimately `where it lives and how fast it arrives` rather than `what a
result is` — rule 7's identity line, which the plan straddles on purpose.
