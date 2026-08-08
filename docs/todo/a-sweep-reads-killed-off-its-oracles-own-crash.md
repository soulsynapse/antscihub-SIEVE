---
title: A sweep reads KILLED off any non-zero exit, including its oracle's own crash
priority: high
status: open
gated_on: nothing
done_when: "uv run pytest tests/scripts/test_mutation_sweep.py -q -k 'a_hung_grandchild_does_not_outlive_the_mutant_timeout or the_mutant_timeout_is_derived_from_the_baseline'"
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

## The refusals hold and the bound does not, so the criterion rotates (2026-08-08)

The criterion this item opened with is delivered and green, re-run
independently: `test_a_red_baseline_is_refused_rather_than_swept` passes, and
`if baseline.returncode != 0: ==> if False:` is killed by it. The over-budget
refusal and the timeout-is-a-kill verdict are killed too — three mutants over
`scripts/mutation_sweep.py` swept against `uv run pytest -q
tests/scripts/test_mutation_sweep.py`, baseline green, one survivor named below.
`done_when` was not edited by the worker, which moved status only to
`awaiting-review`.

It is not `done`, because the folded section above promises a bound and the
bound is not there. `subprocess.run(..., capture_output=True, timeout=T)` kills
the process it started and then blocks in `communicate()` until every inherited
copy of the pipe closes, so a command that spawns a grandchild runs to the
grandchild's completion first: `uv run python -c "sleep(40)"` under a 3 s
timeout raised `TimeoutExpired` after 40.1 s
(`findings/loop/2026.08.08-a-subprocess-timeout-does-not-bound-a-command-whose-grandchild-holds-the-pipe.md`).
`uv run pytest` is exactly that shape and is the only oracle the loop passes
after `--`. The verdict is right — a hang is a kill — and the sweep still
outlives the turn that would kill it, mutant still in the tree, which is the
stall the section was written to end. The case that proves the kill uses
`sys.executable -c`, a direct child with no descendants, so it is green and
tells us nothing about the live shape. Closing the item would certify the bound.

Two smaller things the same sweep and reading turn up. The per-mutant timeout's
derivation is run by nothing: `max(MUTANT_TIMEOUT_FLOOR_SECONDS, 2.0 * elapsed +
1.0) ==> 300.0` SURVIVED, because every case that reaches a timeout passes
`mutant_timeout` explicitly, so both the floor and the factor are written and
unchecked. And `_tail` has two streams and one subject: dropping `stderr` from
its pair survives, as does narrowing its twenty-line window to one, since the
only case that reads it prints a single line on stdout.

`ORACLE_BUDGET_SECONDS`'s comment claims the figure makes "backgrounded, then
killed at turn end" structurally impossible rather than a convention. Nothing
sums the parts — the worst case is the budget plus N timeouts of at least the
30 s floor each — so what the numbers give is a likelihood, and the comment
should say which.

So `done_when` widens rather than closes, onto the two claims the work states
and does not run: a bound that holds when the command has children, and a case
over the derivation the sweep's own survivor exposes. The red-baseline refusal
stays where it is; it is green from here on and a criterion nothing can turn red
certifies nothing.

## The subject came back mutated after the sweep exited (folded 2026-08-08)

A third way the tree is left mutated, and this one is not a killed sweep: twice
in twelve otherwise identical runs over `gui/timeline/geometry.py`, the subject
carried the last mutant's bytes when the *next* command read it, after a sweep
whose own `finally` and byte-exact read-back had both passed and which printed
its results normally
(`findings/loop/2026.08.08-a-restored-sweep-subject-came-back-mutated-after-the-sweep-had-exited.md`;
the mechanism is unaccounted for and the usual external writers were checked and
are absent). Both times the following sweep refused — an anchor it could not
find, then a red baseline — so no verdict was computed against the dirty tree,
which is the refusals above working. What the section adds to this item is that
the existing read-back cannot see this class: it compares the file against the
`original` the same process read at start, so a sweep that *begins* mutated
passes it and a sweep that ends mutated after exiting is past it. A check with
teeth would compare against the subject as git has it, which collides with
running a sweep over uncommitted work under test.
