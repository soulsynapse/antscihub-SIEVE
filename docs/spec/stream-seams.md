# Stream seams: the stream has a module of its own, its kinds one home, dev no way back into the window, and the ledger's records names

Written 2026-11-12 from an architect's reading of v5-monitor at a7ceace5 against v5, which is in no file:
what it found is restated here whole. Built on v5-monitor and done before its pull request, on Kendrick's
word of the same day: a seam left mangled is fixed before the branch is offered, not after. Read with `docs/spec/monitor.md`, whose deliverables built what this
reshapes and whose settled lines this does not reopen; with `sieve_player/graph.py`, whose `Event`, `probe`,
`turn`, `demand` and `_emit` are the stream's emitter as it stands; with `sieve_player/trace.py`,
`ledger.py` and `catalogue.py`, its readers; with `sieve_player/dev/timeview.py` and `window.py`, the two
ends of the one import that runs backwards; and with `tests/test_seams.py`, where a seam is held.

## Why

The monitor's layers are sound: the ledger and the catalogue run from a dump or a hand-built `View`, a
reader is handed a copy it may hold, and what each new module may import is pinned. What the branch left
is a matter of what owns what, and it shows at the next reader of the stream, which
`docs/spec/held-results.md` will be.

`Graph` computes and is also where the stream is emitted, so whatever wants a span in the stream goes
through the compute core, whether or not a node ran it. The GUI thread's slots and paints are timed by
`Graph.turn`; the monitor's own bookkeeping is; and the player's selection sits on `Graph` as `selected`
for no computation's sake, only so a sync's facts carry it. `Event` is in `graph.py`, so `trace` imports
`graph` to name it and `ledger` imports `trace` for the kinds: the ledger holds no graph, as its header
says, and loads one, with the plan, the document and numpy, to replay a file.

The kinds an event may be are written in five places and derived from none. A kind added is five edits,
and the fifth, a deny-list, fails by averaging the new kind into a node's mean with nothing red.

The rest is smaller and of the same sort: a dev module that imports the window it is opened from; records
read by position where a name would say what the position is; two readings of where a walk begins and of
what its rows were, which can disagree; and a poll that judges every walk again each time it fires.

Nothing here changes what the monitor shows. Each deliverable is a change of shape under figures that
stay as they are, so its checks are that a seam now holds and that what was read before reads the same.

## How to read this

As `docs/spec/monitor.md`'s How to read this, whole: deliverables with `Assumes:`, facts read off the
tree, boxes with a `Check:` that is a one-off unless it holds a seam or an invariant, `Open:` lines that
are Kendrick's to settle, `Fork:` lines taken by observation and never unobserved, and nothing that says
how. Here more checks than usual are tests, since a seam is what most boxes assert.

Words, beside monitor.md's. The *emitter* is what builds an `Event` and hands it to `on_event`, with the
state it keeps on each thread to do so: the open spans, the demand, the lane. A *kind* is a value of
`Event.kind`. A *reader* of the stream is anything `on_event` reaches: the ledger, the dump, `Stats`.

## The stream has a module of its own

Assumes: nothing.

Facts to weigh, read 2026-11-12. `Graph` holds `on_event`, `_emit`, `probe`, `turn`, `demand`, `serving`,
`began`, `progress`, `watch`, `selected`, `_hits` and the thread-local `_probing`. `probe` and `turn` share
one stack per thread, and must: the ledger folds on whichever thread emits, inside
`graph.turn("monitor", "ledger")`, so that bookkeeping done at a tool's emit is cut out of the run that
encloses it. `turn` is entered by `window._timed`, which passes the call through untimed while
`self.graph` is None, and by `timeview.Window._timed`, the same. `Graph.watch` is called by
`window._select` and at a video's opening; `plan.facts` takes the selection as an argument and `Graph.sync`
passes `self.selected`. Nothing a node computes reads `selected`. `trace.FIELDS` is read off `Event`, and
`read_dump` refuses a file with other fields. Outside `graph.py` the emitter's methods are called from
`worker.py`, `window.py`, `trace.py`, `dev/simulations.py`, `dev/timeview.py`, `bench.py`, two test files
and five experiments of 2026-11-12, among them ones a ticked box of monitor.md names.

Settled 2026-11-12, Kendrick's word, who makes the emitter and how long it lives: one a
video, made where the `Graph` is made and handed to it, so its life is the ledger's as now and a slot with
no video open is untimed as now; the cost is that the window's guard on a missing video stays. The other
side, one for the window's life, times the GUI thread with no video and gives the ledger a history across
videos, which is a change to what the monitor shows and not this spec's.

Settled 2026-11-12, Kendrick's word, what `Graph` keeps of it by name: `probe`, `demand`, `serving`, `began` and `progress`
stay callable on `Graph` as they are, being said by whoever drives a computation, the worker and
`bench.py`, so no experiment a ticked box names is rewritten; `turn`, `watch` and `selected` leave it,
being no computation's.

Facts added 2026-11-12 on building it. `on_event` is in neither list of the line above: it stays readable
and settable on `Graph`, passing through to the emitter, since
`docs/findings/experiments/2026-11-12-the-figure-on-the-player.py`, which the check under Dev imports no
window has exit as it did, sets and prints `win.graph.on_event`, and `Stats` and `Dump` install
themselves through it. `Stats.event`'s skipped tuple held "slot", "paint" and "monitor" in `graph.py`,
so the third box below could not hold with `Stats` there: `Stats` is in `sieve_player/stats.py`, as
settled under A kind is said once, and its taking a kind by membership is still that deliverable's.
`plan.facts` no longer takes the selection; `Emitter.sync` adds it to the facts a sync carries. No test
drove `turn` or `watch` on a ledger, so the last box is a one-off's.

Settled 2026-11-12, Kendrick's word, on a contradiction found building it: "no experiment a ticked box
names is rewritten" did not hold with `watch` gone from `Graph` and `Event` out of `graph.py`, and each
experiment the move broke is repointed by its one line, what it observes unchanged.
`2026-11-12-the-monitor-on-the-player.py` says `r.stream.watch`; `2026-11-12-the-window.py` and
`2026-11-12-the-window-says-what-is-wrong.py` import `Event` from `sieve_player.stream`;
`2026-11-12-what-the-trace-costs.py` says `g.stream.turn`; and
`2026-11-12-probe-cost-with-the-stream-facts.py` imports `Stats` from `sieve_player.stats`. The line of
monitor.md's header that named `graph.py` for the stream names `stream.py`.

- [x] `Event`, the kinds and the emitter are in one module that imports nothing of `sieve_player`.
  Check: its entry in `test_seams.MAY_IMPORT` is the empty set. It is `sieve_player/stream.py`.
- [x] `trace` and `ledger` import that module and no `graph`; importing `sieve_player.ledger` or
  `sieve_player.catalogue` in a fresh interpreter loads no `sieve_player.graph`, `plan` or `document`.
  Check: `MAY_IMPORT`, and a seam test that reads `sys.modules` after the import in a subprocess.
- [x] `Graph` names no kind that no node ran and holds nothing of the player's selection; a sync's facts
  carry the selection as before.
  Check: a seam test reads `graph.py` for "slot", "paint", "monitor" and "selected"; the graph test of a
  sync's plan stands; `docs/findings/experiments/2026-11-12-the-stream-has-a-module.py` reads a watched
  selection off the next sync and off the walk's record.
- [x] `Event`'s fields and their order are what they were, and a dump written before reads back.
  Check: a dump from a simulation at a7ceace5 replays to a view equal to the one it replays to there;
  the same one-off, over the slot and rewalk simulations.
- [x] A span the ledger's bookkeeping takes on an emitting thread is still cut out of the run that
  encloses it.
  Check: the same one-off, a run's ms with and without a long fold inside its emit.

## A kind is said once

Assumes: The stream has a module of its own.

Facts to weigh. The kinds are a comment on `Event.kind`; `SPANS`, `TURNS` and `OWN` in `trace.py`; `_RAN`,
`_FILE` and `_READS` in `ledger.py`; `COSTS`, `_COLD` and `_HELD_AS` in `catalogue.py`; and the tuple
`Stats.event` returns early on, which this branch extended by six. The ledger and `trace.totals` take a
kind by membership in a set and pass over what they do not know; `Stats` takes whatever it is not told to
skip as a tool's span. `Stats` is made by `bench.py`, `tests/test_graph.py`, `tests/test_trace.py` and one
experiment, and by nothing under `sieve_player`. Its docstring says "the window and bench.py read the
same"; the window reads none. That sentence is reported here and not corrected: which side is wrong is
Kendrick's.

Settled 2026-11-12, Kendrick's word, where `Stats` lives: out of `graph.py`, beside the stream's module, as the reader of it
that `bench.py` uses; it holds a `Graph` only for `snapshot()`'s counters.

Settled 2026-11-12, Kendrick's word, whether `test_one_accumulator_reads_the_stream_for_the_monitor` stands. It asserts by the deleted
monitor's file and class names, which is a thing pinned for having been removed, and `Stats` is a second
accumulator it does not see. It goes, the box below holding what it was for.

Facts added 2026-11-12 on building it. What a kind is, is the tuple of `stream.py` it sits in: `NODES`,
`TURNS`, `OWN` or `INSTANTS`, with `SPANS` the first three and `KINDS` all four. `catalogue.py` names a
kind by the module's value, so its entry in `MAY_IMPORT` holds `stream` beside `ledger`, and `stats`'
holds `stream`: two seams wider than they were, each by the module that imports nothing. Three words
spell a kind and are another thing's name in a reader: "fold" a demand, "monitor" the name the monitor's
own turns carry, and "dump" a key of what a text is handed. `test_seams.NOT_A_KIND` names them by file,
uncounted, and the test holds beside it that no string spelling a kind is what a `kind` is compared with;
a kind held under a name that is not `kind` and compared with one of the three words is what that leaves
unseen. A demand's values are a comment on `Event.demand` as the kinds were on `Event.kind`, which is
reported here and not built. The readers the second box's seam test reads are `ledger` and `stats`: the
dump writes every kind and classifies none, and `trace.totals` takes `SPANS`. The test reads the kinds
each compares an event's `kind` with where it takes one, `Ledger._fold` and `Stats.event`, and the set
it passes over is the test's own, `test_seams.PASSED_OVER`, beside `MAY_IMPORT`: no reader holds a set
that nothing of it reads. The ledger takes a node's span by `NODES` and passes over none. `Stats` takes
the kinds of `stats.MEANS`; what it averaged before it averages now, a "cancel" among them and an
"error" not, which is reported here and not changed. The emitting side still spells a kind where it says one: `graph.py`,
`worker.py`, `window.py` and `dev/timeview.py` pass a string to `probe`'s list or to `turn`, which no
check here reads.

- [x] Every kind is a named value in the stream's module, with what it is: a span of a node's, a span of
  a thread's, a reader's own, or an instant. The sets a reader keeps are drawn from those.
  Check: a seam test finds no kind as a string literal in `trace.py`, `ledger.py` or `catalogue.py`
  outside a set built from the module's. It is `test_a_reader_spells_no_kind`.
- [x] A kind no reader has classified fails a test and is averaged into nothing: `Stats` takes a kind by
  membership, as the ledger does.
  Check: a test feeds `Stats` an event of a kind made up for it and reads no node's mean moved; a seam
  test reads every kind of the module in each reader's sets or in a stated set of those it passes over.
  They are `test_an_event_is_read_by_name_and_refused_short` and `test_a_reader_classifies_every_kind`.

## Dev imports no window

Assumes: nothing.

Facts to weigh. `dev/timeview.py` imports `PaceControl` from `window.py`, and `window.py` imports `dev`;
`dev.show` imports `timeview` inside the call, which is all that keeps the two from importing each other
at load. `PaceControl` reads a `pace.Figure` and `theme` and nothing else of the window. `window` and the
modules under `dev` have no entry in `MAY_IMPORT`. `dev/simulations.py` imports `timeview` at its top and
`tests/test_catalogue.py` imports `simulations` at its top, so the tests of the catalogue, a module that
reaches no Qt, load `window.py` and everything it imports. `dev/__init__.py` says of itself that what is
under it is no part of using SIEVE.

Facts added 2026-11-12 on building it. The control is in `sieve_player/pacecontrol.py`, its class moved
whole, and its entry in `MAY_IMPORT` is `pace` and `theme`. With it gone from `window.py`, importing
`tests.test_catalogue` loads no `sieve_player.window`. `window` and the modules under `dev` still have
no entry in `MAY_IMPORT`; the test below reads `dev` for the one import and holds nothing else of them.

- [x] No module under `sieve_player/dev` imports `window`, and the control the player's header and the
  monitor's both draw is in a module each may import.
  Check: `test_seams` reads the imports of every file under `dev`. It is
  `test_nothing_under_dev_imports_the_window`.
- [x] The control draws as it did.
  Check: `docs/findings/experiments/2026-11-12-the-figure-on-the-player.py` exits as it did.

## The ledger's records have names

Assumes: nothing.

Facts to weigh. `ledger.Node.runs` is a dict from a tuple, (kind, demand, the node asked), to a list,
[count, ms, bytes]. `catalogue.py` reads the list by index or by unpacking on some eighteen lines and
`timeview.py` on none, reading the catalogue's values; `ledger.save` flattens key and value into one list and `saved` cuts it back at 3. A
walk is identified by the tuple (lane, t0) in `Problem.walk`, `Log._seen`, `Log.read`, `text` and
`report`, nine lines of `catalogue.py`, each building or comparing it by hand. A saved history is a session's handover,
written to the temporary folder and named in a copied report.

Settled 2026-11-12, Kendrick's word, whether a history saved before this reads after it: no; `saved` refuses one of
another shape and says so, a history being of the session that wrote it.

Facts added 2026-11-12 on building it. The three values are `ledger.Under`, kind, demand and asked;
`ledger.Total`, count, ms and bytes; and `ledger.WalkId`, lane and t0, made by `Walk.id` alone. The
names are the builder's and Kendrick's to change. Each is a tuple with named fields, so a `Total` is
not written in place: the ledger puts a new one at each span, and makes an `Under` to find it. What
that costs the fold of a span is measured against c0ec2e20 in
`docs/findings/2026-11-12-what-the-trace-costs.md`, its last part. A position still reads what it read,
which is why the tests that key a run by a plain tuple stand unedited and why the dated experiments
that index a run, `2026-11-12-a-cold-window-and-the-clip.py` and
`2026-11-12-the-window-says-what-is-wrong.py` among them, run as written: the first box holds of
`sieve_player` and of `tests`, and of those experiments it does not. A saved history names each field
of a run, and `saved` raises ValueError on a record whose fields are not the ledger's, read before
anything is built of it, so an error from the building is no refusal. The one-off counts a loop over the
runs once, so its count of lines at a7ceace5 is under the fact's above.

- [x] What a node ran under, and what that came to, are each a value with named fields, and nothing
  outside `ledger.py` reads either by position.
  Check: a one-off greps `catalogue.py` for an index into a run; the catalogue's tests stand. It is
  `docs/findings/experiments/2026-11-12-the-ledgers-records-have-names.py`, over every module under
  `sieve_player`.
- [x] A walk's identity is one value, made in one place.
  Check: the same one-off, for `(w.lane, w.t0)` built outside `ledger.py`.
- [x] A view saved and read back is equal to itself.
  Check: the test of `save` and `saved` in `tests/test_ledger.py` stands.

## A span's place in time is the emitter's to say

Assumes: The stream has a module of its own.

Facts to weigh. An event's `ms` is exclusive of the spans opened inside it and its `t` is its start.
`Ledger._span` rebuilds where a span's own time fell, to share it over buckets, from three things no
docstring states together: that on one thread an enclosing span emits after those it opened, that an
opened span names its `reader`, and that one with no reader is enclosed by nothing. The emitter held the
real stack when it emitted. A "slot" or "paint" is not rebuilt: the ledger spreads `ms` from `t`, so one
with a turn inside it is taken to end early by the inner turn's length.

Fork: whether a turn inside a turn is misplaced by enough to read. Observed by a one-off that opens a
"slot" with a long "monitor" turn inside it across a bucket's edge and reads the buckets. Where the slot's
ms land in buckets it did not run in, the box below is added to; where they do not, by more than a
bucket's width, the fact above is corrected and nothing is built.

Observed 2026-11-12, `docs/findings/2026-11-12-a-turn-inside-a-turn.md`. As the Fork words it, a slot of
105 ms with a turn of 500 ms inside it has 93 of its ms in a bucket it did not run in. In the player with
its monitor open, of some 2500 slots and paints none had a span inside it and their thread emitted no
other span. The Fork asks the first observation and it came out misplaced, so by its words the box below
is added to, and it is, unbuilt: the second observation is the builder's, asked for by no line here, and
is no ground for taking the other side.

Open: how a turn's own time is placed. The ledger places a node's span from the stream as it is: a span
emitted later on a thread with an earlier `t` encloses those since, and `reader` says which spans to keep
for an encloser still to come, one with none being kept for nothing. A turn names no reader, so two ways
stand. The ledger alone keeps every turn for an encloser that in the player never comes, which wants a
bound on what it keeps, and a turn enclosing more than the bound is misplaced as now; a node's span with no
reader inside a turn, a tool run from a slot, stays unseen. Or the emitter, which holds the stack, says of
every span what opened it, a turn's `reader` being the span it was opened inside: `Event`'s fields stand
and what `reader` means on a turn changes, the ledger's bookkeeping inside a run's emit is placed by the
same rule, and the `reader` a call site passes to `probe` becomes a thing the emitter already knows.
Of the two the second is the better: the rule beside `Event` then holds of every span with no exception
written into it. Recommended over both, a third: nothing is built and the clause the box gained is taken
out again. The Fork's observation could come out one way only, a slot built with a long turn inside it
across a bucket's edge being misplaced by arithmetic, so it chose nothing; what does choose is whether the
player ever opens a span inside a turn, and in the two sessions observed it did not. The one-off stays to
ask that again when a slot comes to repaint or to run a tool. Either build is a change to what the stream
says or to what the ledger keeps, and so Kendrick's; meanwhile the rule beside `Event` says what a reader
that spreads a turn from its `t` gets wrong.

Facts added 2026-11-12 on building it. The rule is in `Event`'s docstring; `Ledger._span` and
`trace.totals` cite it and restate none of it. The existing ledger test read a run and a run with a read
inside; a fold after the run is added to it.

- [ ] The rule by which a reader places a span's own time is stated once, beside `Event`, and a test
  holds the ledger to it for a run, a run with a read inside, a fold after a run, and a turn with a turn
  inside it.
  Check: a ledger test over hand-built events; the existing one where it already reads the three. It is
  `test_a_span_is_spread_over_its_buckets_and_a_cost_keeps_its_place_along_the_range`, which reads no
  turn inside a turn.

## The poll judges a walk once

Assumes: nothing.

Facts to weigh. `timeview.Window` polls every 250 ms on the GUI thread, and each poll takes a view and
calls `Log.read`, which runs every detector over every finished walk in the history, up to 64. `thrash`
calls `needs` for each walk, and `needs` reads every walk for each node of the plan, so a poll's work goes
as the walks squared times the nodes; `store_name`, `rows` and `_pixels` read every walk again for the
panels. A finished walk that is not its lane's last does not change. The poll is itself in the stream, a
"slot" named "monitor", and `catalogue.gui` gives its share of the wall.

Fork: what the poll costs with a full history. Observed with the monitor's own figure, on the purb
document after sixty-four walks, the monitor shown: the "slot monitor" share of the wall and its longest.
Where it is under the share at which `waits` would name it, nothing is built and the figure is recorded
in a finding; where it is over, a walk that can no longer change is judged once and what was found of it
kept, `slower`'s pair and an entry's `holds` being the only things a later walk moves.

Observed 2026-11-12, `docs/findings/2026-11-12-what-the-poll-costs.md`, offscreen: with sixty-four walks
held a poll took some 48 ms and the polls a fifth of the wall, over the share at which `waits` names a
span, and the log named "slot monitor". The Fork is taken to its second side and built.

Facts added 2026-11-12 on building it. `Log.read` hands each detector the finished walks not yet judged
for the last time, and a walk that is no longer its lane's last is judged in the first read that finds
it so and never again; a detector takes the walks to judge beside the view and judges every finished one
when given none, so one called with a view alone reads as it did. Nothing found of a walk is kept apart
from the entries, which already held it. The same run after: some 12 ms a poll and under a twentieth of
the wall at every length of the history. The panels still read every walk at every poll, which
the finding gives as what is left.

Open: two things the build changed that the Fork did not hand it, built as below and Kendrick's to let
stand or not; the box's second half, "what the monitor shows of it is what it showed", does not hold of
the first. The Fork has `slower`'s pair and an entry's `holds` as all a later walk moves. `thrash` is a
third: `needs` reads every walk in the view for the bytes a node's result came to, and the store's
figures are read off the bucket the walk ended in, so what an entry says of a walk its lane has left, its
target's "needs" and its line's "held", was made again at every poll and could move, as a later walk
under the same key made a result this one only held, or go, as the bucket left the history. Judged once,
it is as the last read before the lane moved on found it. Recommended, to let it stand: it shows only in
an entry that no longer holds, and a line about a past walk that stays as written reads truer than one
that loses its clause when the history turns over. The second: a walk judged for the last time is known
by its id, so a `Log` handed views of two ledgers takes a walk of the second for one of the first where
their ids meet. It counted by the same id before, and the docstring now says one ledger. Recommended, to
let it stand, the monitor's `Log` having one ledger for its life.

- [ ] A walk no later event changes is judged once, and what the monitor shows of it is what it showed.
  Check: `test_the_log_holds_one_entry_a_class_and_subject_counted_cleared_and_ordered` counts the walks a
  detector is handed over three reads; the simulations' tests stand; the finding's second table.

## One reading of a walk's start and of what its rows were

Assumes: nothing.

Facts to weigh. Three classes hold a walk. `worker._Walk` begins one and says so to the stream;
`ledger.Walk` opens at that "begin"; `pace._Walk` opens when a lane's count does not rise, the worker's
signals carrying no beginning. What a walk's rows were is counted twice: by `_Walk.turn` from
`Graph.tally` taken before and after the row, which its docstring says counts another thread's miss, for
the player's control; and by the ledger from the kinds each node emitted, for the monitor. The monitor's
header draws the first and its table the second. monitor.md has the control read "the worker's own signals
and attaches nothing to the probe"; since then the ledger is attached for a video's life, read or not, by
`docs/findings/2026-11-12-what-the-trace-costs.md`.

Fork: how far the two counts differ. Observed on the simulations and on the purb document, served and
live, with scrubs during the walk: ran, held and served by the control beside the ledger's for the walked
node, per walk. Where they agree on every walk, both stand and the finding says so; where they differ, the
Open below is Kendrick's to settle with the difference in front of him.

Observed 2026-11-12, `docs/findings/2026-11-12-two-counts-of-a-walks-rows.md`, offscreen, twenty-nine
walks. The two agree on the twenty-two that read no bake and that no scrub reached into. They differ on
the six served walks, where the control counts a row served when a bake's file was read anywhere under it
and the ledger counts the walked node, which ran, the bake's node being the one served; and on the one
walk a scrub ran a row of first, where the walk found the row held and then folded it, and `ledger._RAN`
takes a node's fold for the node running. Neither is a miscount. Where a walk begins was not observed.

Open: whether the control reads the ledger. Not recommended either way before the fork: the ledger's count
is exact and is a reader's, taken at a poll; the worker's is the control's own and arrives with the row.
After it, the builder's reading and not a settling: the two count different things, a row and a node, so
the control reading the ledger's walked node would draw a served walk as one that ran; and whether a row
on which only a node's fold ran is that node's `ran` is a second question the observation raised, one of
a figure the monitor shows.

## The catalogue's parts

Assumes: The ledger's records have names.

Facts to weigh. `catalogue.py` holds the detectors with their thresholds; `Log`; the values a reader
draws, `Row`, `Resource`, `rows`, `gui`, `machine`, `tight`, `alike`, `needs`; two renderings to text,
`report` and `text`, with `line`, about a hundred and ten lines; and `cold`, `Projection`, `reach` and
`_growth`, about eighty, which three experiments and one test read and the window does not draw, by the
Fork in monitor.md that left the projection "a reading in `catalogue.py` that an experiment prints". Its
header says the values are there "so the monitor and whatever else draws a node read one figure".

Settled 2026-11-12, Kendrick's word, where the text renderings live: a module beside the catalogue that imports it, so how
a report reads changes in a file no threshold is in; the values stay, being the one figure.

Facts added 2026-11-12 on building it. `report`, `text` and `line` are in `sieve_player/report.py`,
moved whole, with the command line that prints an entry a line: it is `python -m sieve_player.report`,
and the catalogue has none. The module's name is the builder's and Kendrick's to change. Three
experiments imported `line` from the catalogue, `2026-11-12-served-scrub-moves-the-walks-cursor.py`,
`2026-11-12-served-bake-upstream-walk.py` and `2026-11-12-a-cold-window-and-the-clip.py`, and each is
repointed by its one line, as settled under The stream has a module of its own; the three places
monitor.md named `catalogue.text` or `catalogue.report` name `report.text` and `report.report`.

- [x] The module the detectors are in renders no report.
  Check: `MAY_IMPORT` has the rendering's module importing the catalogue and not the reverse.

## Not here

Outside this, each for a reason. The shape of `Event`, a record whose `node`, `row` and `facts` mean
different things by kind: settled by the Open under The stream says why in monitor.md, and built on. The
names that collide, `window.catalogue` beside `catalogue.py`, `registry.Entry` beside `catalogue.Entry`,
and "window" for the player's, the walked range, the lane and the monitor's `Window`: Kendrick's own pass,
with the region names already waiting on it. Where the cold projection lives: left where monitor.md's Fork
left it until its observation is made again. And any figure the monitor shows.
