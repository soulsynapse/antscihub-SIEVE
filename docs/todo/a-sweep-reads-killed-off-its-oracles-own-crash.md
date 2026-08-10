---
title: A sweep reads KILLED off any non-zero exit, including its oracle's own crash
priority: high
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/scripts/test_mutation_sweep.py -q -k an_unparseable_mutant_is_refused_before_the_oracle_runs"
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

## The case covers the line and not the verdict, so it rotates again (2026-08-10)

The criterion is green from here, `done_when` was not edited by the worker, and
the case discriminates the line it was written for: the combined redirection
mutant and each of `stdout=out,` and `stderr=err,` alone all turn it red,
re-verified against the working tree rather than through the sweep.

It does not reach this item's title. `run_sweep` hands the same oracle to the
baseline and to every mutant, so an oracle that writes 1 MiB unconditionally
fills the buffer on the baseline first: under `PIPE` the failure is
`SweepError("the test command did not finish inside the 20s oracle budget")`
raised before any mutant is applied, not a KILLED scored against one
(`findings/loop/2026.08.10-a-case-whose-oracle-is-talkative-at-the-baseline-is-refused-before-any-mutant-is-scored.md`).
The rotation above asked for "a false KILLED on a mutant the tests do not kill",
and the only oracle shape that produces one is quiet on the original bytes and
talkative on the mutated ones — quick green baseline, mutant blocked at the
buffer, timed out, scored KILLED under `PIPE` and SURVIVED with the redirection.
`done_when` rotates onto that case. The existing case stays; it is the only red
the refusal has for a reason other than a red baseline, and it needs a name that
claims the capacity rather than the verdict.

The new case's docstring states the KILLED mechanism as though the case reached
it, so it is wrong in the tree for the same reason `_run_bounded`'s is, and the
correcting run owns both paragraphs. The clauses listed as next are unchanged
and unstarted: the docstring's own correction, the compile-the-mutant gate,
`_tail`'s uncased halves, and `ORACLE_BUDGET_SECONDS`'s comment.

## What landed (2026-08-10)

`test_an_oracle_talkative_only_on_the_mutant_is_not_scored_killed`, and nothing
else. Its oracle exits 0 while `limit = 100` is in the subject and writes 1 MiB
to each stream once the mutant has removed it, so the baseline is green, no
refusal fires, and the mutant is the first invocation that can block — the
asymmetry the section above says is the only shape that reaches a verdict. The
true verdict is SURVIVED and the case asserts it.

The mechanism was read outside the sweep's alphabet, which is what the finding
this rotation came from asks for: `run_sweep` called in-process against a `PIPE`
twin of `_run_bounded`, `SweepError` caught and printed apart from the verdict,
returning `[True]` — a scored KILLED, not a refusal. Red through the sweep is
also recorded — the combined redirection mutant and each of `stdout=out,` and
`stderr=err,` alone all KILLED — but on the finding's own reading a sweep cannot
tell which red it got, so that is capacity evidence and not mechanism evidence.
The finding carries the amendment.

Untouched, in the order the section above lists them: `_run_bounded`'s docstring
and this rotation's own predecessor docstring — the correcting run owns both
paragraphs and the capacity case's name with them — then the compile-the-mutant
gate, `_tail`'s uncased halves, and `ORACLE_BUDGET_SECONDS`'s comment.

## The verdict is reached, and the criterion rotates onto the deterministic member (2026-08-10)

The title's false KILLED is reached by a case for the first time, re-verified
independently rather than read off the transcript: the criterion is green here,
`done_when` was untouched and `status` moved only to `awaiting-review`, the
redirection mutant turns the new case red through the sweep, and the mechanism
reproduces outside the sweep's alphabet — `run_sweep` in-process against a `PIPE`
twin of `_run_bounded` returns `[True]`, a scored KILLED with no `SweepError`
raised, against a mutant whose true verdict is SURVIVED. The whole module is
green.

It is not `done`, because everything the criterion could not reach is in the
tree rather than ahead of it, and one run and one commit satisfies all of it:
the compile-the-mutant gate — the deterministic member of the false-KILLED
class, which fires on every subject under every oracle and is the only remaining
clause a `-k` can assert — and, riding with it because they are the same file
and the same reading, the three paragraphs that now describe a mechanism their
subject does not have. `_run_bounded`'s docstring credits the redirection with a
promptness `Popen.wait` supplies;
`test_an_oracle_whose_output_outgrows_the_pipe_buffer_is_scored_by_its_exit`
states the KILLED mechanism as though its own case reached it, when what it
establishes is capacity, and its name claims the verdict the case above is the
one to claim. `_tail`'s uncased halves and `ORACLE_BUDGET_SECONDS`'s
"structurally impossible" comment are still here and still smallest.

`done_when` rotates onto the gate. What the paragraphs wait on is checkable in
one command beside it — `grep -rn "is_scored_by_its_exit" tests/scripts` comes
back empty once the capacity case carries a name that claims capacity, and the
docstrings are corrected in the commit that renames it.

## What landed (2026-08-10)

The gate and the three paragraphs, which the section above asks for in one commit.
`refuse_unparseable` compiles the mutated bytes and raises `SweepError` before
they are written, so an unparseable mutant is refused where a non-unique anchor
is and no verdict prints for it; the module and `run_sweep` docstrings say the
baseline structurally cannot reach this member, since it is red on the mutated
bytes only.

`test_a_mutant_that_leaves_the_subject_unparseable_is_refused` runs both forms of
one mutant against an oracle that `exec`s the subject — the shape every real
oracle has and the probes in this module deliberately do not. Shown red on the
unchanged tree by the defect itself: `    a = 100 ==>    a = 100  # tuned`, the
indentation-shifted form the separator's padding produces, printed `KILLED` and
exited 0 where the case wants a refusal, while the same mutant written with its
indentation intact SURVIVED in the assertion above it. That pairing is the case's
whole content — the two answers are a space apart and the report does not say
which you got. Killed after the gate landed by
`refuse_unparseable(subject, mutant, mutated) ==> pass` and by
`compile(mutated, str(subject), "exec") ==> None`, 2 killed 0 survived over
`scripts/mutation_sweep.py` against the module as oracle.

The paragraphs: `_run_bounded`'s docstring now attributes the bound to the tree
kill and the redirection to capacity, cited to the finding that measured it;
`test_an_oracle_whose_output_outgrows_the_pipe_buffer_is_scored_by_its_exit` is
`test_an_oracle_that_outgrows_the_pipe_buffer_still_finishes`, and its docstring
says its own oracle is talkative at the baseline too, so it establishes only that
such an oracle finishes and hands the verdict to the case beside it.
`grep -rn "is_scored_by_its_exit" tests/scripts` is empty. The two-part-fix
finding is closed on its own terms by these two paragraphs; the 2026-08-08
crashing-oracle finding stays open, amended, because only the deterministic
member is a refusal and the intermittent crash is still scored.

Untouched and unstarted, in the order the section above lists them: `_tail`'s
uncased halves — dropping `stderr` from its pair survives, as does narrowing the
twenty-line window to one — and `ORACLE_BUDGET_SECONDS`'s comment, which claims
its figure makes a stall "structurally impossible" where nothing sums the parts.

## The gate holds, and the refusal is paid for after the oracle has been (2026-08-10)

Re-verified rather than read off the transcript: the criterion is green here, the
whole module is 27 green, `uv run pytest -q --ignore=tests/gui` is 1036 green with
the load-sensitive bench case not firing this time, `ruff check` and
`format --check` are clean, `done_when` was untouched and `status` moved only to
`awaiting-review`. Red-before was reproduced by deleting the `refuse_unparseable`
call from the loop and running the case: it fails on `assert 0 == 1` with
`KILLED    a = 100` and `1 killed, 0 survived` on stdout — the false KILLED
itself, not some neighbouring red. The rename is complete
(`grep -rn "is_scored_by_its_exit" tests/scripts` is empty) and both corrected
docstrings say what their subjects do.

Not `done`, and the reason is in the tree rather than ahead of it. Two clauses the
criterion never reached are still unstarted — `_tail`'s uncased halves and
`ORACLE_BUDGET_SECONDS`'s comment — and a third arrived with the gate: every
refusal `run_sweep` can raise about a mutant is a pure function of the original
bytes and the mutant, and every one of them is raised from inside the per-mutant
loop, after the oracle budget has already been spent on the baseline and after
earlier mutants have been scored and discarded. `apply_mutant`'s two anchor
refusals were always there; `refuse_unparseable` joins them, and it is the one a
hand-typed mutant list hits routinely, because the padding rule below is a
one-space trap on every indented line. A sweep of twenty mutants whose
nineteenth will not compile pays the baseline and eighteen oracle runs and prints
nothing. `done_when` rotates onto that: the refusals move ahead of the baseline,
so a mutant list that cannot be applied is refused before any subprocess starts,
and the case names a sweep whose second mutant is unparseable and asserts the
oracle was never invoked.

Riding with it in the same commit, and covered by prose rather than by the
criterion: `_tail`'s two uncased halves, and `ORACLE_BUDGET_SECONDS`'s
"structurally impossible" comment.

## What landed (2026-08-10)

The hoist and both ride-alongs, which the section above asks for in one commit.
`run_sweep` applies and compiles every mutant into a `prepared` list before the
baseline, so all three per-mutant refusals — anchor absent, anchor duplicated,
bytes that will not compile — are raised with no subprocess started, and the
per-mutant loop consumes bytes it no longer computes.

`test_an_unparseable_mutant_is_refused_before_the_oracle_runs` runs a two-mutant
sweep whose second mutant is the indentation-shifted form, under an oracle that
writes a marker file on every invocation and exits 0, and asserts the marker is
absent — no baseline, no first-mutant run. Shown red on the unchanged tree by the
defect itself: `assert not marker.exists()` failed on `assert not True`, the two
oracle invocations the old ordering paid for before refusing.

`_tail`'s two uncased halves are covered by
`test_a_refusal_shows_both_streams_and_more_than_its_last_line`, over a fabricated
`CompletedProcess` loud on stdout and terse on stderr. It passes on the unchanged
tree, since the gap was the case and not the code, so red is shown the way the
neighbour item `every-bounded-declaration-is-run-not-read.md` shows it, by
sweeping the lines it exists for: dropping `("stderr", finished.stderr)` from the
pair and `lines: int = 20 ==> 1` both KILLED, 2 killed 0 survived over
`scripts/mutation_sweep.py` against the module as oracle — the two mutants this
item recorded as survivors.

`ORACLE_BUDGET_SECONDS`'s comment now says the figure bounds the baseline alone
and that a sweep's worst case is the budget plus one per-mutant timeout each, no
smaller than the floor, so "backgrounded and killed at turn end" is unlikely for a
handful of mutants under a mostly-passing oracle rather than structurally
impossible.

The hoist paid for itself inside this run: the first attempt at the `_tail` sweep
mistyped the replacement's indentation and was refused in well under a second with
no oracle run, where the old ordering would have spent a baseline plus one full
pytest session first.

Nothing here is left over: the two clauses the previous section lists as riding
along are both in the commit, and the item's own criterion is the hoist.

The trap itself is not folded in here as work, because the gate is the ruling the
previous rotation already took over re-founding the signal: `parse_mutant`'s
comment says "an anchor's own indentation still counts, only the separator's
padding does not", and that is true of the anchor and false of the replacement —
` ==> ` eats the replacement's first indent space, so `A ==> B` for an indented
`B` always arrives one space short and the sweep now refuses it with a message
that says to add the space back. That is loud and operable. What it is not is
recorded correctly: the two mutants this item's section above and the
2026-08-08 finding's amendment both quote as `2 killed, 0 survived` are refused
when re-run verbatim, and reproduce only with a compensating space
(`findings/loop/2026.08.10-a-done-items-mutation-anchor-is-deleted-and-nothing-re-runs-it.md`).
