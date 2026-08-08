---
title: A sweep reads KILLED off any non-zero exit, including its oracle's own crash
priority: high
status: awaiting-review
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

## The baseline is also the clock (folded 2026-08-08)

Two sweeps against `gui/expander.py` stalled the loop the same way on
2026-08-08: the oracle was `uv run pytest -q tests/gui
tests/bench/test_gui_loop_budget.py` for five mutants, which outlives the
harness's foreground command window, so the sweep was backgrounded, then killed
when the run's turn ended — with the current mutant still patched into the
source. A killed sweep never reaches its `finally`, so the failure leaves the
tree mutated and uncommitted, and the next run inherits it.

The baseline this item already asks for is the instrument that prevents this:
run it under the oracle budget as a hard timeout, and refuse — rather than
sweep — when it does not finish green inside it, with an explicit flag for a
deliberately broad run. A refused broad oracle is also the stricter
measurement: KILLED is any non-zero exit, so one red test suffices, and a
mutant that only a distant test kills is a coverage gap the narrow oracle
exposes and a broad one hides. The green baseline's elapsed time then bounds
each mutant run, and a mutant that stops the command terminating counts as
KILLED — it broke the program — which closes the third stall shape, the hung
mutant, that the unbounded `subprocess.run` invited.
