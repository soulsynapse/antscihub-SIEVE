---
title: A sweep reads KILLED off any non-zero exit, including its oracle's own crash
priority: high
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/scripts/test_mutation_sweep.py -q -k an_oracle_whose_output_outgrows_the_pipe_buffer_is_scored_by_its_exit"
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

### The refusals are not the net, because the next command is usually a criterion (folded 2026-08-09)

The section above closes on the two occurrences being caught by the sweep that
followed them, so no verdict was computed against a dirty tree. A third
occurrence, on `gui/chain_stack.py` and recorded in the same finding, was not:
what ran next was the item's own `done_when`, which went red on the work just
written and reads as a defect in it. A criterion has none of the refusals — it
has an oracle, and the oracle answers. That is the ordinary shape of a run, not
an unlucky one: a sweep is what a worker does *before* re-running the criterion
it is about to report on. So the argument that this class is loud enough to be
left open should rest on something other than the next command being a sweep.

## A mutant that will not compile is the deterministic false KILLED (folded 2026-08-08)

This item opened on a false KILLED that fires once in nine runs. There is one
that fires every time, on any subject, under any oracle, and the review of
`274278d` hit it while re-running a worker's sweep
(`findings/loop/2026.08.08-a-crashing-test-command-is-indistinguishable-from-a-killed-mutant.md`,
dated section). `parse_mutant` strips the separator's own padding from both
sides, so a replacement written with the anchor's indentation loses one leading
space and the subject stops parsing; `IndentationError` on import is a non-zero
exit and prints KILLED. The correctly-indented form of the same mutant SURVIVED,
which is the answer the review acted on — the two verdicts are one space apart
and the output does not say which you got.

The baseline this item's first section won cannot reach it: the baseline runs
the *original* bytes, and every way a mutant makes the subject unparseable is
downstream of that. So the class the item names has a deterministic member and
a cheap gate for it — compile the mutated bytes and refuse the mutant, as a
non-unique anchor is already refused, rather than scoring it. A `SyntaxError`
is a mutant that was never applied, not one that was killed, and it is the same
refusal-not-report shape the rest of this item argues for. Whether that gate is
what lands, or whether the whole KILLED signal is re-founded on the mutant's own
test failing (which subsumes it, and which the finding names as the real fix),
is this item's decision and not a second item's.

## The sweep leaves a sidecar, so the next red command names the mutant (folded 2026-08-09)

The subsection above closes on this class being quiet whenever the next command
is a criterion rather than a sweep, and on the third occurrence costing four
invocations and a wrong hypothesis before the tree was the thing being looked
at. What that argues for is not a fix — the mechanism is still unaccounted for,
and the structural answer, never writing a mutant into the working tree at all,
is a larger decision this must not pre-empt — but a detector, so that the wrong
reading costs one line of output instead of a diagnosis.

The shape: `scripts/mutation_sweep.py` leaves a sidecar recording the subject it
swept and the exact replacement text of every mutant it applied, and a failing
pytest session reads that sidecar, checks the subject for those texts, and
prints one line naming the subject, the replacement found in it, and the path to
`findings/loop/2026.08.08-a-restored-sweep-subject-came-back-mutated-after-the-sweep-had-exited.md`.

The signature must be the replacement text present in the subject, not that the
subject changed. A worker editing the file after a sweep is the ordinary case —
a sweep is what precedes re-running the criterion — so a hash captured at the
sweep's exit false-positives on every ordinary run, while no legitimate edit
reintroduces a mutant's bytes. It is also the check the folded section above
says the read-back cannot be: it compares against neither `original` nor git, so
it holds over uncommitted work under test.

Two things the work will get backwards unless they are said here. The sidecar
must survive a clean exit rather than being removed in the `finally`: all three
recorded occurrences followed a sweep that exited 0 and printed its results, so
a sidecar deleted on success is a detector that can never fire. And it carries a
`completed` flag separate from its list of applied replacements, because a sweep
killed mid-mutant never reaches its `finally` at all — the second mode in this
item, recorded in the folded 2026-08-08 section above — and an incomplete
sidecar is what catches that one. One artifact, both modes: the flag says a
sweep that did not finish left the tree mutated, the replacement bytes say one
that did.

## The bound landed and the criterion rotates onto the half nothing covers (2026-08-10)

The bound the section above asked for is delivered and re-verified: the criterion
that rotated onto it is green independently, `done_when` was not edited by the
worker, and `_terminate_tree(process) ==> process.kill()` and the derivation's
own recorded survivor `max(MUTANT_TIMEOUT_FLOOR_SECONDS, 2.0 * elapsed + 1.0)
==> 300.0` both reproduce as KILLED. `run_sweep` no longer calls
`subprocess.run` at all.

The third mutant the commit reports as killed does not reproduce.
`stdout=out, stderr=err ==> stdout=subprocess.PIPE, stderr=subprocess.PIPE`
SURVIVED an independent sweep over the same two cases
(`findings/loop/2026.08.10-a-two-part-fix-is-reported-as-two-kills-and-the-half-that-carries-it-is-the-other-one.md`),
and the reason is that `_run_bounded` never calls `communicate()` — it waits on
the process handle, which returns on time whatever the streams are. So
`_run_bounded`'s docstring, the finding it cites, and the commit message all
credit the redirection with a promptness `Popen.wait` supplies, and the
docstring is the one in the tree.

The redirection is still load-bearing, and for a reason that belongs to this
item rather than a neighbour: nothing drains the pipes — no `communicate()`, no
reader thread — so a PIPE oracle that writes past the buffer blocks in its own
`write`, never exits, and is timed out and scored KILLED. That is a false KILLED
on a mutant the tests do not kill, which is this item's title, and `uv run pytest
-q` on a red baseline clears 64 KB without effort. `done_when` rotates onto a
case over it, because a departure whose stated reason is wrong and whose real
reason has no case is indistinguishable from one that could be deleted.

Two clauses this criterion does not reach, in the order they should rotate next:
the docstring's own correction, which no `-k` can assert; and the
compile-the-mutant gate two sections above, which is the deterministic member of
the false-KILLED class and fires on every subject under every oracle. `_tail`'s
uncased halves and `ORACLE_BUDGET_SECONDS`'s "structurally impossible" comment
are still here and still smallest.

## What landed (2026-08-10)

`test_an_oracle_whose_output_outgrows_the_pipe_buffer_is_scored_by_its_exit`,
and nothing else. An oracle writing 1 MiB to each stream and exiting 0, swept
for a mutant that survives: under `PIPE` the child blocks at the buffer, is
timed out, and prints KILLED, which is this item's title over a mutant the
tests do not kill. There was no implementation to revert, so red was shown the
way the neighbour item `every-bounded-declaration-is-run-not-read.md` shows it,
by sweeping the line the case exists for: `stdout=out, stderr=err ==>
stdout=subprocess.PIPE, stderr=subprocess.PIPE` KILLED, and each of
`stdout=out, ==> stdout=subprocess.PIPE,` and `stderr=err, ==>
stderr=subprocess.PIPE,` KILLED alone, against the combined mutant's recorded
SURVIVED. The finding carries the amendment.

The two clauses the section above lists as next are untouched: the docstring's
own correction, and the compile-the-mutant gate.
