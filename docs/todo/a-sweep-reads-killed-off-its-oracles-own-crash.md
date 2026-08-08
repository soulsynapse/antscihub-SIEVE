---
title: A sweep reads KILLED off any non-zero exit, including its oracle's own crash
priority: high
status: open
gated_on: nothing
done_when: "uv run pytest tests/scripts/test_mutation_sweep.py -q -k 'a_red_baseline_is_refused_rather_than_swept'"
opened: 2026-08-08
---

# A sweep reads KILLED off any non-zero exit, including its oracle's own crash

`run_sweep` records `finished.returncode != 0` as KILLED and never establishes
that the command exits zero on the unmutated subject. So a test command that
fails, errors, collects nothing, or dies in a native frame prints a clean sweep
over mutants it never reached — and a clean sweep is what closes an item.

The four lies `mutation_sweep.py`'s docstring is built from are all false
SURVIVEDs, which convict correct work and cost a wasted run. This one is a false
KILLED, which certifies work that was not done and is never asked about again.
`uv run pytest -q tests/gui` was measured crashing on a Windows access violation
once in nine runs on 2026-08-08
(`findings/loop/2026.08.08-a-crashing-test-command-is-indistinguishable-from-a-killed-mutant.md`),
which is the live instance; the class is wider than Qt, because a mistyped path
after `--` collects nothing and exits 5 too.

The shape the criterion names is a baseline run: the command once on the
original bytes, before any mutant, and a refusal rather than a report if it is
not green — the same treatment a missing or duplicated anchor already gets, and
for the same reason. Whether the baseline's captured output is shown on refusal
is the open question the work should answer; a refusal naming only "the command
was already red" sends the reader back to run it by hand, and `run_sweep`
currently discards `stdout` and `stderr` entirely.

One extra invocation per sweep, not per mutant.
