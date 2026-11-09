# Solver: a series tool that carries state from row to row, and a worker that steps it

Written 2026-11-08, revised the same day after an architecture review; the first five
deliverables were ticked that day, the worker's last. The two after it were added the same day,
from an architect review of the branch at b588358c and ticked that day; every box is ticked.
Read with the registry's facet table and type report (`python -m sieve_player.registry`), the live
statement of what a tool may offer and what feeds what, and with
docs/findings/2026-11-08-bake-window-fit.md, the measurement this spec answers. docs/spec/bake.md
is the spec before it and nothing here changes a bake; the series bake's relation to a stepped
chain is in Open.

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
csv and tracks-csv read one row. track, kinematics, transitions and travel read the row and state
carried from the rows before it, and are written as steps; travel's state is the row before, as
transitions' is, and it was the last of the four written so, on 2026-11-08 after the walk stepped.
smooth, tracks-filter and resolve read the whole window, rows not yet walked included, and change
their past as the window grows. The second group is the solver case and the whole measured cost;
the third is the bound on what stepping can reach.

Stepping is a property of the chain, not of a tool. A tool that steps reading a tool that rewrites
its past cannot step, since its input at a row it has passed is not what it was. So the chain has
a steppable prefix and a rerun suffix, and the planner's job is to know where the line falls and
say so. On the current tools the suffix is tables of a few hundred rows: kinematics was measured at
65 ms over 600 rows in docs/findings/2026-11-02-kinematics-and-spacing.md, against track's 200 to
250 ms a rerun in the bake finding; tracks-filter, resolve and the stepped walk itself are read in
that finding's second half, where the suffix is what bounds the cadence.

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

Words. A node is *fed* when the plan finds it wired and typed, as today. A stepping tool is
*stepped* a row: handed one folded row and the state it returned for the row before, it returns the
next state and that row's share of its result. A node that is not stepped *runs whole*, the
contract every series tool meets today. The *prefix* is the stepped part of the chain and the
*suffix* the rest. The probe's event for the decoder decoding one row forward is "decode", renamed
from "step" on 2026-11-08 so that the word is the tool's alone.

## A series tool may step

Assumes: nothing.

The contract a series tool meets today, the whole stack in and a result out, stays and stays
mandatory: it is what a tool that needs the window has, and it is the oracle for one that steps.
A tool that steps offers, beside it, one more entry point: given the state it returned for the row
before, None at the first, the folded row and its index, it returns the next state and one row of
its result, the table or the value that `run` would put at that index. The player accumulates
those rows into the node's result as the walk stacks the walked node's rows, so after row i the
accumulated result is the result `run` gives over the rows up to i, field for field and dtype for
dtype, for every i. Stepping changes when a result arrives and never what it is. A tool that cannot
promise the equality does not step.

Facts to weigh, as the tree stands at 5b96276e and to be verified against it. tools/track.py's
`link` writes `rec["id"]` at row r and never revisits it, counts `signal[r]` from `hits` as they
stand at r, and prunes `live` forward only, so its step is the loop's body with `live` and
`next_id` as the state, and the row it returns is final when returned; `min_rows` and `lost_rows`,
which read like whole-window rules, act at the row and hold under this. kinematics carries a deque
per id and transitions the row before, the same shape. None of the three needs to render state into
a result after the fact, which is why there is no second entry point for that: the per-row output
is the result, and the suffix needs the accumulated prefix result at each emit anyway, so the
player holds it, sizes it under STACK_BYTES with the stack, and the state a tool keeps is the small
thing, live tracks and deques, not a copy of its output. The oracle is cheap because `run` is
kept: a stepping tool costs its author one function, and a tool that steps wrongly is found by a
mechanical per-row comparison rather than by a wrong sidebar. State is opaque to the player and
never the memo's: `Memo` sizes by `nbytes`, the finding already shows it double-counting one
shared buffer, and a state with references into the stack would count the stack again. The
registry reads facets and never calls a tool, as its README says, so the oracle is a test
helper over the tools' own fixtures and the registry only reports that a tool offers the facet.

- [x] The registry's facet table lists the step facet with the hint line a tool adds to supply
  it, and the type report says of each series tool whether it steps; the registry's check does
  not run a tool.
  Check: a test reads the facets and the report for a tool that steps and one that does not.
- [x] A helper in tests/ holds a stepping tool to its oracle over a series: the row returned at
  each index equals `run`'s result at that index over the rows up to it, every field and dtype,
  and the accumulated rows equal `run`'s result over the whole; a tool that steps but peeks ahead
  fails with the first row it diverged at.
  Check: a test runs the helper over a tool that steps correctly and over one built to peek, and
  reads pass and the named row.
- [x] track, kinematics and transitions step and pass the helper over their existing fixtures;
  count, size, spacing, reduce, csv, tracks-csv, smooth, tracks-filter and resolve do not step and
  their behaviour is unchanged.
  Check: the three tools' tests call the helper; the others' tests pass unchanged.

## The plan knows where stepping ends

Assumes: A series tool may step.

The chain in run order has a longest prefix every node of which steps, and a suffix that runs
whole, and which is which is decided by the chain's shape and not by a tool alone: a stepping tool
whose source does not step runs whole, and the first node that runs whole ends the prefix for
every node after it. The verdict is the plan's, made at sync, shown beside the standing, and never
saved.

Facts to weigh. The plan already walks the chain in run order and already decides, per node, fed
or unrun with a standing that says why, so the verdict is one more thing read off a pass it makes;
if that pass has moved by the time this is built, the fact to keep is that the verdict is made
where fed and unrun are, not somewhere of its own. The standing's contract is why a node does not
run, empty when it runs, and the canvas tooltip and the pane's line read it so; a node run whole
runs, so the verdict is a field of its own on the plan's entry and not a standing. The ants
documents under video-tests/ at ba71e6f5 head the chain with track, size and count off blobs and
run travel under track, with none of tracks-filter, resolve or kinematics in them, so under the
rule their whole chain is prefix once travel steps, which it did not when this was written; the
Why above says what is and is not measured of a suffix's cost. If a whole-window
tool heavy enough to matter arrives, the
plan's verdict is what makes its cost legible on the node rather than hidden in the chain, which
is the Houdini and Blender case: the non-stepping node is a visible kind of thing, not a slow
version of the same thing.

- [x] The plan names, for each node in the chain, whether the walk steps it or runs it whole, and
  a stepping tool downstream of a whole-run node is run whole.
  Check: a test plans track → tracks-filter → kinematics and reads step, whole, whole; and
  track → kinematics → transitions and reads step, step, step.
- [x] A node run whole because of what it reads carries, in a field beside its standing, the node
  that ended the prefix; a stepping node and a whole-run node whose own tool does not step carry
  nothing there, and the standing's meaning is unchanged.
  Check: a test reads the field and the standings of the first chain above.
- [x] A served series head, a bake read back in place of a walked head, is stepped by the plan's
  verdict, and so is a stepping chain under it, as a walked head's would be.
  Check: a test lands a blobs bake on the node track reads and reads the plan's verdict for the
  head and the chain. The walk's half of this, the served rows reaching the chain one at a time
  through the probe, is a box under The window walk extends, since nothing walks a step before it.

## One walk, two ranges

Assumes: The plan knows where stepping ends. This is a refactor with every signal unchanged, done
before the walk is taught to step so that stepping is written once and not into each copy.

The clip walk is the window walk over the clip without the densities, run behind a finished
window walk, and the two are today two copies of one job whose state, reset and cadence are
written out twice and have already diverged on cadence: the clip's chain runs under
`CHAIN_SHARE`, the window's under `every`, because the rerun was unaffordable over a clip. The two
ranges are one walk told whether to keep densities, how far to go, and what cadence rule to emit
under; the throttle becomes that job's parameter here and goes in the next deliverable, when
stepping removes its reason.

Facts to weigh. The pairing is visible in the names: `_walk_one` and `_clip_one`, `_emit_series`
and `_emit_clip`, and the fields `_stack`/`_cstack`, `_bytes`/`_cbytes`, `_folded`/`_cfolded`,
`_i`/`_ci`, `_walk_gen`/`_clip_walk_gen`, with the reset tuple written out by hand three times in
`_serve`. The clip walk's `CHAIN_SHARE` is the adaptive cadence the window walk never received,
which is what a second copy does over time: one gets the fix. The differences that are real and
stay are three: the clip walk keeps no densities, runs only behind a finished window walk, and is
what a series bake writes from. Everything else that differs between them today is drift, and a
seams test is the cheapest witness that the drift does not come back. The Open item on a series
bake writing row by row would give the clip range no stack at all; the job holding a stack or none
is the shape that leaves that door open without building it.

- [x] The window walk and the clip walk are one job with one state and one reset, instantiated
  over the window with densities and over the clip without, each under its own cadence rule.
  Check: a test walks a window and then a clip under the probe and reads the same per-node run
  pattern over both up to cadence; a seams test reads no clip-only twin of a walk field or method.
- [x] Everything the clip walk promised stands: it waits behind the window walk, a frame change
  abandons it and its rows, stopping it short leaves its rows standing with the count saying so,
  and a series bake writing from its result is abandoned with it.
  Check: tests/test_baking.py's clip-walk cases pass unchanged.

## The window walk extends

Assumes: One walk, two ranges.

A walked row reaches the stepping prefix once, as one folded row, and the prefix's state moves
forward by one; the suffix runs whole over the prefix's accumulated result at each emit. The
cadence at which results reach the sidebar is bounded by the GUI's appetite and by the emit's own
cost, which stays linear in the rows walked, since each emit gates and hands out the whole prefix
result and the trace redraws it; compute is no longer the cadence's reason. The sidebar's result
after any emit is what the whole-stack chain would have given over the rows walked, as it is
today.

Facts to weigh. The worker today emits the chain every `every` rows, thirty, and at the window's
end, and `_run_chain` is handed the stack sliced to the rows walked and re-folds it through each
head's `fold` under a per-stack cache; the finding measured track's rerun at 200 to 250 ms on the
crossings window, about twenty times across 590 rows, 4 to 5 s of a 7 s cold walk and all of a
rewalk. The quadratic is in the rerun's cost growing with the rows walked, so a cadence change
alone moves the constant and not the shape; a cadence of every row would put a quadratic back in
the emit, so it is not the default this spec assumes. A parameter change on a stepping node under
this deliverable costs what a single rerun costs today, once, and nothing after; the same change
today costs a rerun at every emit until the window is done. `rerun_series` is the path a
series-only change already takes, so the reset has a home. The densities are per row and never the
chain's, and nothing here touches them.

- [x] Across a window walk each stepping node is stepped each row exactly once and never handed
  the stack; each whole-run node runs once per emit over the prefix's accumulated result; and the
  series results emitted at each cadence equal the results the unstepped chain gives over the same
  rows.
  Check: a test walks a synthetic window under the probe, counts steps per node per row and runs
  per node per emit, and compares each emit's results to the whole-stack chain's.
- [x] A rewalk of a window the memo holds, nothing changed, costs the stepping prefix one step per
  row and no rerun, so its time is the per-row step summed and not the chain summed per emit.
  Check: a test rewalks under the probe and reads one step per row for each stepping node and
  zero whole runs for them.
- [x] A served series head's rows reach the stepping chain under it one at a time, each node
  stepped once per row and never handed the file's rows whole, as a walked head's would be.
  Check: a test serves a baked blobs file into track and reads the per-row stepping through the
  probe.
- [x] A change to a stepping node's params, or to anything upstream of it, discards its state and
  accumulated result and the walk steps it again from the window's first row off the stack it
  holds; a change to a node after the prefix reruns the suffix over the prefix's standing result
  and steps the prefix nothing.
  Check: a test changes track's `max_step` and reads the steps restart at row zero; changes
  tracks-filter's `lo` and reads no step of track and one run of the suffix.
- [x] The result cadence is one setting in one place, read by the walk over either range and not
  encoded in a worker constant per range; the time-share throttle is gone.
  Check: a test changes the setting and reads the emit count over a fixed window and over a clip.
- [x] A stepping tool's state is the tool's own and opaque to the player: nothing in the player
  reads into it, sizes it, memoizes it, or keeps it past the walk that made it; the accumulated
  result is the player's, counted toward the walk's bytes as the stack is.
  Check: a test walks a stepping chain and reads the memo's entries and the probe's bytes for the
  stepped node, finding no state held under its key and the result's bytes in the walk's count.

Worth a look: the crossings document's window walk, cold and rewalk, through
`sieve_player/dev/monitor.py`, beside the finding's 7 s and 4–5 s, as the second half of
docs/findings/2026-11-08-bake-window-fit.md, with tracks-filter's and resolve's per-run
cost read off the probe beside kinematics' 65 ms; and whether a shorter cadence than thirty reads better or
worse to a user tuning while a walk is in progress, now that compute no longer sets it. Read
2026-11-08 and written as that second half; the cadence question is open there with its numbers.

## The worker schedules; jobs hold their state

Assumes: The window walk extends.

The worker's thread stays one, since the decoder has one cursor and the store's Windows file lock
rests on readers being reaped there. What it holds today beside the thread is a priority ladder,
scrub, then a bake's change of state, then a bake row behind a finished window, then the walks,
written as one loop over one bag of fields whose resets are repeated by hand. The ladder is the
worker's; each rung's state is a job's. After this deliverable the worker reads as the ladder and
the condition it waits on, and each job as what it does with one turn, so that a job's reset is
one place and the ladder's order is one list.

Facts to weigh. The worker at 5b96276e is 578 lines, one class with 44 private fields, and
`_serve` is about 130 lines; `_Bake` already holds a bake's own state, and after One walk, two
ranges the walk is a job too, so two of the three jobs are shaped before this begins. The ladder's
order is load-bearing and is what the existing tests pin: a scrub before anything so the frame a
user jumped to appears first, a bake's change of state before a bake row, a bake row only behind a
finished window walk, the clip walk last. The one-thread constraint is also load-bearing and is not
what this deliverable loosens: `Readers.reap` asserts the worker thread, the decoder's scrub cursor
is the walk's cursor set aside, and Nuke's engine and Houdini's cook both run interactive and
background work through one evaluation path for the same reason the player does, that the source
is one cursor. What the DCCs separate is who decides what runs next from what each job does when
it runs; the player's thread already is the former and this deliverable is only the latter. A
split that changes any emitted signal, refusal or order has gone further than the deliverable asks.

- [x] Every signal the worker emits, every request it answers and every refusal it gives is as it
  was: the walk, clip and bake tests pass unchanged, and a test drives the jobs through one
  sequence, a scrub landing mid-walk, a bake asked mid-walk, a clip walk after, and reads the order
  they were served against the ladder.
  Check: the existing tests and the new sequence test.
- [x] A job's state is held by the job and reset in one place, and a generation change reaches a
  job as the scheduler's word and not by each job comparing counters.
  Check: a seams test reads one reset per job and no generation comparison outside the scheduler.
- [x] The monitor's `serving` lanes name the job that served each event as they do today.
  Check: tests/test_monitor.py passes unchanged.

## The wait predicate means a rung will turn

Assumes: The worker schedules; jobs hold their state.

The condition `_serve` waits on and the ladder that serves are two readings of one question, is
there a turn to take, and they can disagree: a job can say it is pending while the ladder, on the
same pass, finds no rung due and takes nothing, and the loop then spins through the lock until
some ask changes the answer. The predicate should be the ladder's own word, so that waking means
turning.

Facts to weigh, as the tree stands at b588358c and to be verified against it. `_Bake.pending()`
is true for a frame bake with rows left, and the ladder serves a bake row only behind a finished
window; a window stalled with rows left and nothing feeding its walked node, the moment between a
graph edit on the GUI side and the `invalidate` that follows it, leaves `pending()` true and
nothing turning. The pre-refactor loop had the same gap, so no test pins it either way. The
`fed` test is made once per pass in `_serve` and the bake's rung reads `win.i >= win.length`
beside it; the duplication is where the disagreement lives.

- [x] The condition `_serve` waits on is true only when the next pass of the ladder will begin or
  turn some job, and each job's due-ness is read in one place by the predicate and the ladder
  alike.
  Check: a test stalls a window unfed with rows left while a frame bake has rows to write, holds
  there, and reads the ladder passed no more times than asks were made; the seams test reads one
  due-ness per job.
- [x] Every signal, request and refusal is as it was.
  Check: the walk, clip, bake and ladder tests pass unchanged.

## A job is built from what it reads and emits

Assumes: The wait predicate means a rung will turn.

Each job holds a reference to the whole worker and reaches through it for the graph, the cadence,
the store, the signals it emits and two of the worker's private methods, so a job cannot be made
without a `QThread` under it and the seam the job decomposition was reaching for, a job driven by
a test with a graph and a few signals, is not there. A job should take what it reads and what it
emits at construction, named, and the worker should be the one thing that knows all of them.

Facts to weigh, as the tree stands at b588358c and to be verified against it. `_Walk.w` is typed
`object` and `_Walk` reaches `w.graph`, `w.every`, `w.failed`, `w.densityReady`, `w._run_chain`
and `w._served_head`; `_Bake` reaches `w.graph`, `w.store`, `w.baked`, `w.bakeDone`,
`w.bakeRefused` and `w.walk_clip`; `_Scrub` reaches `w.graph`, `w.rowReady` and `w.failed`.
`_Walk` already takes its progress, ready and refused signals as fields, which is the shape the
rest should follow. `_run_chain` reads only the graph and is called by both ranges and by
tests/test_bake.py, so it is a function over a graph that moves with its callers. The two walks
are built by position at `Worker.__init__`, two booleans and three signals in a row, which the
rebuild of their construction should name. The seams test pins `begin` to `_serve` and no
generation comparison anywhere, and both pins stand through this.

- [x] Each job holds the graph it reads, the cadence and the signals it emits, and reaches nothing
  through the worker; the chain run and the served-head test are functions over a graph; the
  walks are constructed with every field named.
  Check: the seams test reads no field or attribute of a job that names the worker and no
  positional argument past the first in a `_Walk` construction; tests/test_bake.py's call of the
  chain run follows it.
- [x] Every signal, request and refusal is as it was, and the `serving` lanes name the job as they
  do today.
  Check: the walk, clip, bake, ladder and monitor tests pass unchanged.

## Non-goals

- A frame tool that carries state. A frame tool's row is keyed and memoized on its inputs at that
  row, and a row that reads the row before it breaks the key model the memo, the bake and the plan
  rest on. Houdini and Blender both hold this line, the Solver SOP and the simulation zone being
  the only constructs that cross it, and the player holds it at the series kind: a running
  background, if one is wanted, is a series tool reading frames, not a frame tool with memory.
  Decided 2026-11-08.
- A second entry point that renders a tool's state into its result after the fact. No tool in the
  tree needs one, and the per-row contract is what keeps state small and the result the player's;
  a tool that cannot say its row at the row runs whole. Decided 2026-11-08.
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
- Whether travel steps: it does, decided 2026-11-08, on what its row reads and not on its cost.
  Its row reads the row before and nothing else, the shape transitions has, and a tool whose row
  is causal steps by nature; cost was the wrong criterion, since on the window travel is cheap
  either way and on the clip it was the ants documents' whole suffix, rerun every cadence rows
  with the throttle gone. The programs around it draw the line in the same place: Bonsai's
  displacement is a Scan over the stream and buffering is the marked construct; SLEAP tracks
  forward and culls over the finished video; TRex, DeepLabCut and idtracker.ai derive speed from
  stored positions after the fact, and their non-causal step is a smoothing, which is this
  player's smooth and not travel. A centred or smoothed speed, if wanted, is a separate tool fed
  from travel or kinematics, as the equality rule requires.
- What a step may read beside its row: the state, the folded row, its index within the range and
  the params, and not the frame rate or the absolute row, decided 2026-11-08. A series tool
  reasons in rows. The frame rate is the axis's, not the row's, and the axis is what the player's
  transforms change: a bake at a stride records `fps / inc` in its sidecar, a served head's rows
  are on that rate, and the plan's `axis` and `off` exist because a node can sit in another row
  space than the display, so a rate handed to a tool per row would mean a different thing at
  different nodes of one graph. The tools already hold this line: track's `lost_rows` and
  `min_rows`, kinematics' `span` and its speed in pixels per row are in rows, and nothing in
  tools/ reads `Series.fps`. Seconds are for whoever knows the axis, the timeline, the header and
  the sidecar, as the trace draws a value and never a derived one. A bout with a duration
  threshold is a bout with a threshold in rows, as `lost_rows` is. What would reopen this is a
  tool whose answer needs the absolute row rather than the range index, a per-row timestamp
  column say, and that is the export's to add at write time, where it has the Series, as resolve
  reads `start` and runs whole. Noted from the architect review of the branch.
- Whether a fast window walk changes the default window length, which is 10 s for the stack and
  the decoder cache and not for the chain. docs/findings/2026-11-08-bake-window-fit.md has the
  fit numbers; the chain's are the Worth a look above.
