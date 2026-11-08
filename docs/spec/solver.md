# Solver: a series tool that carries state from row to row, and a worker that steps it

Written 2026-11-08; no box below is ticked. Read with the registry's facet table and type report
(`python -m sieve_player.registry`), the live statement of what a tool may offer and what feeds
what, and with docs/findings/2026-11-08-bake-window-fit.md, the measurement this spec answers.
docs/spec/bake.md is the spec before it and nothing here changes a bake; the series bake's
relation to a stepped chain is in Open.

## Why

On the crossings document the window walk's time is not the frames. The bake finding put decode
and rescale at a tenth of a row and the series chain at the rest, and the chain's cost is one
tool's: every so many rows the worker hands track the stack walked so far and track assigns ids
afresh from the first row, so the chain's reruns across a window sum to a cost quadratic in the
window's length over the rerun cadence. A rewalk with nothing changed, every frame answered by the
memo, still pays all of it. The bake has nothing to say to this, and neither does any cache: the
work is repeated, not fetched.

Every DCC with a time axis met this and drew the same line. A node whose row depends only on its
inputs at that row is pulled per row and cached by key, which is what the player's frame tools and
memo are. A node whose row depends on its own previous row is a different construct: Houdini's
Solver SOP and DOP simulations, Blender's simulation zone, cook forward carrying state, cache what
they have cooked, replay from the last state they hold when asked for a row beyond it, and start
over when a parameter changes, which the user sees as a reset. Nuke has no live solver and instead
makes the stateful analysis, Tracker, CameraTracker, an explicit pass that writes its result into
the node as data; the player's series bake is that shape already. What none of them does is
re-simulate from the first frame each time the viewer refreshes.

The player's series tools split three ways by what a row needs. count, size, spacing, reduce,
csv and tracks-csv read one row. track, kinematics and transitions read the row and state carried
from the rows before it, and are already written as loops that carry it. smooth, tracks-filter and
resolve read the whole window, rows not yet walked included, and change their past as the window
grows. The second group is the solver case and the whole measured cost; the third is the bound on
what stepping can reach.

Stepping is a property of the chain, not of a tool. A tool that steps reading a tool that rewrites
its past cannot step, since its input at a row it has passed is not what it was. So the chain has
a steppable prefix and a rerun suffix, and the suffix on the current tools is cheap, tables of a
few hundred rows; the planner's job is to know where the line falls and say so.

For a tool author, carried state is the natural shape of most behavioural analysis, a state per
animal, a bout, a contact with hysteresis, an ethogram classifier. Written against the contract
as it stands, each of those is a loop over the whole stack paid once per emit. Written as a step
it is paid once per row, and the author never meets the cadence.

## How to read this

Each `##` below is a deliverable: an `Assumes:` line naming what it builds on, a sentence of why,
then done-when assertions, each a box with a `Check:` that is a test in `tests/`. A box is ticked
by a session once its test passes in the tree; a session never unticks or rewrites an assertion,
and before building toward an unticked box checks whether the tree already meets it. Where a
result is worth Kendrick's eye before the next deliverable leans on it, a `Worth a look:` line says
what to look at; it is not a gate. Nothing here says how. Any deliverable whose `Assumes:` are all
done is available; among those the earlier one in the file first. The branch is done when every
box is ticked.

## A series tool may step

Assumes: nothing.

The contract a series tool meets today, the whole stack in and a result out, stays and stays
mandatory: it is what a tool that needs the window has, and it is the oracle for one that steps.
A tool that steps offers, beside it, a way to be fed one folded row at a time with the state it
handed back for the row before, and a way to render the state it holds into the result the sidebar
draws. The result rendered after row i is the result the whole-stack contract gives over the rows
up to i, for every i, so stepping changes when a result arrives and never what it is; track's
`min_rows` and `lost_rows`, which read like whole-window rules, are rendering of carried state and
hold under this. A tool that cannot promise the equality does not step, and the registry's check
is what finds one that promised wrongly.

Facts to weigh, as the tree stands at 5b96276e and to be verified against it. tools/track.py's
`link` is already a loop over rows carrying `_Track` objects with predict and take, so its step is
the loop's body and its render is the pass that reads `min_rows` and `hits` into the signal; what
is new is the seam, not the algorithm. kinematics reads each id's previous record and transitions
reads the row before, the same shape. The oracle test is cheap because `run` is kept: a stepping
tool costs its author a step and a render and nothing else, and a tool that steps wrongly is found
by a mechanical comparison rather than by a wrong sidebar. State that is opaque cannot be sized,
which is why it is not the memo's: `Memo` sizes by `nbytes`, and the finding already shows it
double-counting one shared buffer; a state object with references into the stack would count the
stack again. Keeping state out of every cache also means a stepping tool's author owes the player
nothing about what the state is or how big.

- [ ] The registry's facet table lists what a stepping tool offers, with the hint line a tool adds
  to supply it, and the type report says of each series tool whether it steps.
  Check: a test reads the facets and the report for a tool that steps and one that does not.
- [ ] The registry's check holds a stepping tool to its oracle: over a synthetic series the result
  rendered after each prefix equals the whole-stack result over that prefix, every field and
  dtype, for every prefix length, and a tool that steps but peeks ahead fails the check with the
  first row it diverged at.
  Check: a test runs the check over a tool that steps correctly and over one built to peek, and
  reads pass and the named row.
- [ ] track, kinematics and transitions step and pass the check; count, size, spacing, reduce,
  csv, tracks-csv, smooth, tracks-filter and resolve do not step and their behaviour is unchanged.
  Check: the three tools' tests gain the prefix equality over their existing fixtures; the others'
  tests pass unchanged.
- [ ] A stepping tool's state is the tool's own and opaque to the player: nothing in the player
  reads into it, sizes it, memoizes it, or keeps it past the walk that made it.
  Check: a test walks a stepping chain and reads the memo's entries and the probe's bytes for the
  stepped node, finding no state held under its key.

## The plan knows where stepping ends

Assumes: A series tool may step.

The chain in run order has a longest prefix every node of which steps, and a suffix that runs
whole, and which is which is decided by the chain's shape and not by a tool alone: a stepping tool
whose source does not step runs whole, and the first node that runs whole ends the prefix for
every node after it. The verdict is the plan's, made at sync, shown where standing is shown, and
never saved.

Facts to weigh. The plan already walks the chain in run order and already decides, per node, fed
or unrun with a standing that says why, so the verdict is one more thing read off a pass it makes;
if that pass has moved by the time this is built, the fact to keep is that the verdict is made
where fed and unrun are, not somewhere of its own. The ants chain as tuned under video-tests/ is
track, then tracks-filter or resolve, then kinematics, so under the rule its prefix is track alone
and the suffix is the rest; that suffix runs over track's rendered tables, a few hundred rows of
small tables, and on the finding's numbers its cost is a small fraction of track's rerun. If a
whole-window tool heavy enough to matter arrives, the plan's verdict is what makes its cost
legible on the node rather than hidden in the chain, which is the Houdini and Blender case: the
non-stepping node is a visible kind of thing, not a slow version of the same thing.

- [ ] The plan names, for each node in the chain, whether the walk steps it or runs it whole, and
  a stepping tool downstream of a whole-run node is run whole.
  Check: a test plans track → tracks-filter → kinematics and reads step, whole, whole; and
  track → kinematics → transitions and reads step, step, step.
- [ ] A node run whole because of what it reads says so in its standing, naming the node that
  ended the prefix, and a node stepping says nothing extra.
  Check: a test reads the standings of the first chain above.
- [ ] A served series head, a bake read back in place of a walked head, is fed row by row to a
  stepping chain under it as a walked head would be.
  Check: a test serves a baked blobs file into track and reads the plan's verdict and the walk's
  per-row feeding through the probe.

## The window walk extends

Assumes: The plan knows where stepping ends.

A walked row reaches the stepping prefix once, as one folded row, and the prefix's state moves
forward by one; the suffix runs whole over the prefix's rendered result at each emit. The
cadence at which results reach the sidebar is a repaint matter and bounded by the GUI's appetite,
not a compute budget, and the sidebar's result after any emit is what the whole-stack chain
would have given over the rows walked, as it is today.

Facts to weigh. The worker today emits the chain every `every` rows, thirty, and at the window's
end, and `_run_chain` is handed the stack sliced to the rows walked and re-folds it through each
head's `fold` under a per-stack cache; the finding measured track's rerun at 200 to 250 ms on the
crossings window, about twenty times across 590 rows, 4 to 5 s of a 7 s cold walk and all of a
rewalk. The quadratic is in the rerun's cost growing with the rows walked, so a cadence change
alone moves the constant and not the shape. A parameter change on a stepping node under this
deliverable costs what a single rerun costs today, once, and nothing after; the same change today
costs a rerun at every emit until the window is done. `rerun_series` is the path a series-only
change already takes, so the reset has a home. The densities are per row and never the chain's,
and nothing here touches them. The equality rule means the cadence can be anything the GUI
tolerates, down to every row; what that looks like to a user tuning is the Worth a look below.

- [ ] Across a window walk each stepping node is fed each row exactly once and never the stack;
  each whole-run node runs once per emit over the prefix's result; and the series results emitted
  at each cadence equal the results the unstepped chain gives over the same rows.
  Check: a test walks a synthetic window under the probe, counts feeds per node per row and runs
  per node per emit, and compares each emit's results to the whole-stack chain's.
- [ ] A rewalk of a window the memo holds, nothing changed, costs the stepping prefix one feed per
  row and no rerun, so its time is the per-row step summed and not the chain summed per emit.
  Check: a test rewalks under the probe and reads one feed per row for each stepping node and
  zero whole runs for them.
- [ ] A change to a stepping node's params, or to anything upstream of it, discards its state and
  the walk feeds it again from the window's first row; a change to a node after the prefix reruns
  the suffix over the prefix's standing result and feeds the prefix nothing.
  Check: a test changes track's `max_step` and reads the feeds restart at row zero; changes
  tracks-filter's `lo` and reads no feed to track and one run of the suffix.
- [ ] The window walk's result cadence is one setting in one place, read by the walk and not
  encoded in a worker constant per walk.
  Check: a test changes it and reads the emit count over a fixed window.

Worth a look: the crossings document's window walk, cold and rewalk, through
`sieve_player/dev/monitor.py`, beside the finding's 7 s and 4–5 s, as the second half of
docs/findings/2026-11-08-bake-window-fit.md; and whether the sidebar updating every row, now
affordable, reads better or worse than every thirty while a walk is in progress.

## One walk, two ranges

Assumes: The window walk extends.

The clip walk is the window walk over the clip without the densities, run behind a finished
window walk, and the two are today two copies of one job whose state, reset and cadence are
written out twice and have already diverged on cadence: the clip's chain runs under
`CHAIN_SHARE`, the window's under `every`, because the rerun was unaffordable over a clip. With
stepping, the throttle has no reason to exist, and the two ranges are one walk told whether to
keep densities and how far to go.

Facts to weigh. The pairing is visible in the names: `_walk_one` and `_clip_one`, `_emit_series`
and `_emit_clip`, and the fields `_stack`/`_cstack`, `_bytes`/`_cbytes`, `_folded`/`_cfolded`,
`_i`/`_ci`, `_walk_gen`/`_clip_walk_gen`, with the reset tuple written out by hand three times in
`_serve`. The clip walk's `CHAIN_SHARE` is the adaptive cadence the window walk never received,
which is what a second copy does over time: one gets the fix. The differences that are real and
stay are three: the clip walk keeps no densities, runs only behind a finished window walk, and is
what a series bake writes from. Everything else that differs between them today is drift, and a
seams test is the cheapest witness that the drift does not come back.

- [ ] The window walk and the clip walk are one job with one state and one reset, instantiated
  over the window with densities and over the clip without; the clip's chain emits on the same
  cadence rule as the window's, and the time-share throttle is gone.
  Check: a test walks a window and then a clip under the probe and reads the same per-node feed
  and run pattern over both; a seams test reads no clip-only twin of a walk field or method.
- [ ] Everything the clip walk promised stands: it waits behind the window walk, a frame change
  abandons it and its rows, stopping it short leaves its rows standing with the count saying so,
  and a series bake writing from its result is abandoned with it.
  Check: tests/test_baking.py's clip-walk cases pass unchanged.

## The worker schedules; jobs hold their state

Assumes: One walk, two ranges.

The worker's thread stays one, since the decoder has one cursor and the store's Windows file lock
rests on readers being reaped there. What it holds today beside the thread is a priority ladder,
scrub, then a bake's change of state, then a bake row behind a finished window, then the walks,
written as one loop over one bag of fields whose resets are repeated by hand. The ladder is the
worker's; each rung's state is a job's. After this deliverable the worker reads as the ladder and
the condition it waits on, and each job as what it does with one turn, so that a job's reset is
one place and the ladder's order is one list.

Facts to weigh. The worker at 5b96276e is 578 lines, one class with 44 private fields, and
`_serve` is about 130 lines; `_Bake` already holds a bake's own state, so one of the four jobs is
half-shaped. The ladder's order is load-bearing and is what the existing tests pin: a scrub
before anything so the frame a user jumped to appears first, a bake's change of state before a
bake row, a bake row only behind a finished window walk, the clip walk last. The one-thread
constraint is also load-bearing and is not what this deliverable loosens: `Readers.reap` asserts
the worker thread, the decoder's scrub cursor is the walk's cursor set aside, and Nuke's engine
and Houdini's cook both run interactive and background work through one evaluation path for the
same reason the player does, that the source is one cursor. What the DCCs separate is who decides
what runs next from what each job does when it runs; the player's thread already is the former
and this deliverable is only the latter. A split that changes any emitted signal, refusal or
order has gone further than the deliverable asks.

- [ ] Every signal the worker emits, every request it answers and every refusal it gives is as it
  was: the walk, clip and bake tests pass unchanged, and a test drives all four jobs through one
  sequence, a scrub landing mid-walk, a bake asked mid-walk, a clip walk after, and reads the order
  they were served against the ladder.
  Check: the existing tests and the new sequence test.
- [ ] A job's state is held by the job and reset in one place, and a generation change reaches a
  job as the scheduler's word and not by each job comparing counters.
  Check: a seams test reads one reset per job and no generation comparison outside the scheduler.
- [ ] The monitor's `serving` lanes name the job that served each event as they do today.
  Check: tests/test_monitor.py passes unchanged.

## Non-goals

- A frame tool that carries state. A frame tool's row is keyed and memoized on its inputs at that
  row, and a row that reads the row before it breaks the key model the memo, the bake and the plan
  rest on. Houdini and Blender both hold this line, the Solver SOP and the simulation zone being
  the only constructs that cross it, and the player holds it at the series kind: a running
  background, if one is wanted, is a series tool reading frames, not a frame tool with memory.
  Decided 2026-11-08.
- Checkpoints of a stepping tool's state, replaying to a row from the nearest held state, and with
  them any copy or pickle contract on state. Nothing asks for a jump into a stepped range yet; the
  window is walked from its start.
- Making the whole-window tools step by approximation, smooth as a causal filter or tracks-filter
  over the rows so far. Each is a different tool with a different answer, and the spec's equality
  rule is what keeps step from quietly becoming one.
- The memo counting a live bake node's identity result twice, and a served frame node going
  unmemoized, both seen in docs/findings/2026-11-08-bake-window-fit.md. Neither is the chain's
  cost and each is its own decision.

## Open

- Whether a stepping head lets the series bake write row by row as a frame bake does, instead of
  from the clip walk's finished result. It would make a series bake abandonable at a row and bound
  by the disk rather than the clip's stack; it also changes what a part file of a series means.
  Waits on the first series bake over a clip long enough to mind.
- What a reset looks like. A parameter change on a stepping node starts it from the window's first
  row, which Blender and Houdini show as a reset; the sidebar today holds the old result until the
  new one lands. Whether the hold or a visible restart is right is Kendrick's call once the walk
  is fast enough that the difference is seen.
- Whether a fast window walk changes the default window length, which is 10 s for the stack and
  the decoder cache and not for the chain. docs/findings/2026-11-08-bake-window-fit.md has the
  fit numbers; the chain's are the Worth a look above.
