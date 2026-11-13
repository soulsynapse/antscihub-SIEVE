# Monitor: the stream carries why, a ledger keeps it over time, a catalogue names what is wrong, and one window shows the three

Written 2026-11-12 from the conversation that read `docs/findings/2026-11-12-served-bake-upstream-walk.md`,
on v5-monitor, branched from v5 at cce7cb8e. Read with that finding, which is the case
this spec is argued from; with `sieve_player/graph.py`, whose `Event` and `Graph.probe` are the stream as it
stands; with `sieve_player/worker.py`, whose ladder decides what each event served; with
`sieve_player/trace.py`, the stream's file and the GUI thread's lateness sampler's reader; with
`sieve_player/dev/monitor.py` and `monitor_views.py`, the monitor this one succeeds; and with
`docs/findings/2026-10-31-window-fit-and-lru-thrash.md`, `2026-11-08-bake-window-fit.md` and
`2026-11-09-crop-cold-walk.md`, where every class of trouble named below was first met by hand.

## Why

A served bake that spared its walk nothing read as a slightly slower walk, and nothing on screen said
why. The finding took a script, a second table summed off the raw events, and a reading of `_Walk.turn` to
say that crop ran six hundred times for no reader but its own density. Each of the three things that hid
it is a property of the monitor as built, not of that fault: the stream does not carry why a run happened,
so a run nobody needed is the same event as one the walk asked for; the monitor accumulates per node under
one fixed reading, the latest walk a node ran in, and that reading is wrong the moment the plan stops
reaching the node; and it shows a state, the figures now, where a slowdown is a change, something that was
one figure and became another.

So three layers, each usable without the one above it. The stream gains the facts a reader cannot
reconstruct: the demand a run answered, the plan a walk ran under, the hits that emit nothing today, and
which range a row belonged to. A ledger keeps the stream over time, in buckets of wall time and in one
record per walk, and holds no opinion. A catalogue is a list of detectors, each a function from what the
ledger holds to the problems it can show, each problem attached to a node or a store and carrying its cost
in the walk's own unit, so problems rank against each other and against the walk. The window draws the
ledger as it scrolls and lists the catalogue's problems beside it. A detector is written once and read in
three places: the window, the terminal, and a dump replayed after the fact.

The separation Kendrick asked for, surfacing apart from analysis, is the line between the ledger and the
catalogue. The frame it borrows without naming is a query planner's: `plan()` is pure, so it states what a
row should cost before anything runs, and a problem is most often a disagreement between that statement
and what the stream then says ran. A monitor that only observes cannot see an unused resource; one that
holds a prediction can. The per-resource half is Gregg's USE reading, utilization, saturation and errors
asked of each store in turn.

Four things bound what that buys, and each has its own place below. A catalogue holds only what was
once found by hand, so a slowdown of no known class must still leave something to hand over. The stream is
the worker's, and a slowdown that is felt is as often the GUI thread's; the player's figures on
purb-settings sit well under the offscreen ones for a reason no finding has taken apart. A monitor
repainting on the GUI thread is a load on the thing it reports, and has to show its own. And a history
that begins when the window opens misses whatever prompted opening it, which makes what a continuously
attached ledger costs a measurement to take before deciding when it is attached.

A catalogue is only as good as its proof that each entry fires on its fault and on nothing else. Each
class therefore has a simulation, a small script that builds the fault on purpose with the player's own
Graph and Worker, and the check for a class is that its simulation surfaces it, alone, and that a healthy
walk surfaces nothing. The served-bake fault is left in the tree on this branch for exactly that reason:
it is the first entry's real-footage witness, and whether the walk stops folding behind a served node is a
decision this spec does not make.

## How to read this

Each `##` below is a deliverable: an `Assumes:` line naming what it builds on, a sentence of why, facts
read off the tree, then done-when assertions, each a box with a `Check:`. Since 2026-11-12, on Kendrick's
word, a check is by default a one-off: a script under `docs/findings/experiments/` or a simulation's
exit, run when the box is built and again when the question comes up, its output recorded where the box
says or in the commit that ticks it. It is a test in `tests/` only where what it holds is a seam or an
invariant, something a later change elsewhere could break without anyone looking: that a dump replays
to what the live ledger held, that a module imports no Qt, that a detector fires on its fault alone. A
check written before that date as a test stands as it was ticked; an unticked one that names a test is
read as naming the behaviour, and the session building it chooses the form by this rule. A box is ticked by a session once its check passes in the tree; a session never unticks
or rewrites an assertion, and before building toward an unticked box checks whether the tree already meets
it. Where a result is worth Kendrick's eye before the next deliverable leans on it, a `Worth a look:` line
says what to look at; it is not a gate. Nothing here says how. Any deliverable whose `Assumes:` are all
done is available; among those the earlier one in the file first. The branch is done when every box is
ticked. `Open:` lines are choices of form, Kendrick's to settle by editing the line; a session builds on
the recommendation they carry only where the line says it may.

Much of what would help is not known until a part is driven, and this spec does not guess it. A `Fork:`
line names something a session or Kendrick can observe once the part before it exists, and what holds on
each side. A session that reaches a fork makes the observation, writes it where the line says, a finding
or the check's own output, and takes the side it gives; it does not take a side unobserved, and a fork
whose observation is Kendrick's use waits for him. What driving a part shows to be missing is added as a
box under its deliverable, with the observation that prompted it; the assertions already there are not
rewritten to fit.

Words. The *stream* is what `Graph.on_event` receives. A *demand* is what asked for a computation at the
top: the walk's row, a density's fold, the display's scrub, a bake's row. A *lane* is which of the worker's
ranges a row belonged to, the window's or the clip's, or the scrub or the bake beside them. A *walk* is one
pass of a lane over its range, from a start or restart to its last row. The *ledger* is the stream's
consumer that keeps it over time. A *bucket* is one fixed slice of wall time in the ledger. A *problem* is
one thing a detector found: its class, its *subject*, the node or store it is about, a line saying what,
and its cost. The *catalogue* is the detectors. The *log* is the problems the catalogue has surfaced in
this session, one entry per class and subject. A *simulation* is a script that builds one fault on
purpose. A node is *watched* when the plot shows it: the selection, or pinned. The *old monitor* is
`Monitor`, `MonitorWindow` and `monitor_views.py` as they stand at the branch point.

## The stream says why

Assumes: nothing.

Three faults in the finding could not be told from the events, and each for a missing fact rather than a
missing analysis.

Facts to weigh. `Event` is frozen with every field required, and `trace.FIELDS` is read off it, so a dump
gains whatever the record gains and `read_dump` refuses a file with other fields. `Graph.probe` emits
nothing on a memo hit, by its docstring's own statement, so hits exist only as `Memo.hits`, one count for
every node. `_compute` is entered from four places, `compute`, `walk_row`, `density` and a `Frames` read,
and none says which to the probe. `serving()` sets "walk" for the window's turns and the clip's alike, and
the clip walk is built with `probes=False`, so it emits no progress event: the old monitor's rows, rate and
unprobed time are the window's, and a clip walk's runs land in whichever window row is open. The `sync`
event carries every node's key and nothing else of the plan. A served reader's decoder has `on_evict`
unset, so its cache discards silently; the plate decoder's and the memo's discards are events already.

Open: whether the new facts are fields on `Event` or one payload field per kind. Recommended, and what a
session may build on: the reader and the demand as fields, since every run and read carries them, and one
`facts` field for what only a boundary carries, the plan on a sync and the counters on a progress. The
existing `keys` and `length` stay as they are.

- [x] Every run, read and fold event names the demand it answered, at any depth: the walk, a fold and
  whose, the display, a bake. A computation a fold opened is told from one the walk opened even when the
  node and row are the same.
  Check: a graph test walks a row and folds a node off the walked path, and reads the walked node's run
  under the walk's demand and the off-path node's run, and the read it opened, under that fold's.
- [x] Every run and read a `Frames` read opened names the reading node, so the reads across one wire can
  be counted.
  Check: the same test reads, for a node with two readers, a run naming the reader that reached it first.
- [x] A sync event carries the plan it began: for each node its kind, whether it is fed, static, served,
  stepped or run whole and by which node, and what each input reads; beside them the walked node, the
  shown and overlaid nodes and the pinned set.
  Check: a graph test serves a node, syncs, and reads from the event alone that the node is served and
  that the node upstream of it is fed and read by nothing the walk reaches.
- [x] Memo hits are counted per node and leave on the next progress event, with each store's bytes held,
  limit, hits, misses and discards as that event found them; no event is emitted per hit.
  Check: a graph test walks twice, and reads zero hits for a node on the first walk's events and one a row
  on the second's, and the memo's held bytes on a progress event equal to `Memo.bytes` then.
- [x] The clip walk's rows are their own lane and it emits progress as the window does; no event of a
  clip row reads as the window's.
  Check: a worker test runs a window then a clip walk and partitions every event by lane, with each lane's
  progress rows counting from one to its range.
- [x] A served reader's cache reports what it discards into the stream under the served node's key.
  Check: a reading-back test reads a baked clip through a reader whose cache holds two rows and finds a
  discard event for the first.
- [x] The old monitor and `Stats` read the same figures off a window walk as before the lane and the
  clip's progress existed.
  Check: `tests/test_monitor.py` and the Stats tests pass unchanged but for the fields an `Event` built by
  hand must now carry.
- [x] A walk's beginning is in the stream: a begin event in the walk's lane, carrying the range's first
  row and its length, at each start and each start over. Added 2026-11-12 on driving The ledger: the
  chain's run at a range's end is emitted after the range's last progress, so with no mark it read as
  the next walk's first row, and a progress event says how long a range is and not where it starts.
  Check: the worker test of the two lanes reads one begin for each range, and a ledger fed its events
  gives the window's last chain run to the window's record.
- [x] A hit counted in a lane before its walk began is not reported on that walk's first row. Added
  2026-11-12 on driving The ledger: the hits of a row a restart cancelled left on the new walk's first
  progress, where a node the row never touched read as held.
  Check: the graph test of the hits computes a held node, begins a walk, and reads no hit on its first
  progress.

Worth a look: what the probe costs with the new facts, by `bench.py`'s cold fill beside the figure it
gives on v5; `docs/findings/2026-11-12-probe-cost-with-the-stream-facts.md` holds the figures, and is where
a later one sits beside them.

## The ledger

Assumes: The stream says why.

The old monitor's figures are right for the question it was built on and cannot be asked another, because
what it keeps is already the answer. The ledger keeps what happened, cut two ways, and every reading is a
function over it.

Facts to weigh. The old monitor resets on a progress row below the last and holds each node's latest walk
in `_last`, which is the reading that kept video, crop and rescale in the cold line after they stopped
running. It buffers the runs between a restart and the next progress event so they count toward the new
walk's first row; the same boundary exists for any consumer. Its unprobed figure is the wall between two
progress events less what was probed inside them. `Dump` appends on the emitting thread and does
everything else on its own, after the GIL-handoff cost its docstring records; a consumer the GUI reads
from has the same constraint from the other side, a painter must not hold a lock the worker's emit waits
on. `window.Lateness` measures how late the GUI thread's timer fires and exists only while a dump is
attached.

- [x] The ledger is fed events and samples and nothing else: it imports no Qt, holds no reference to a
  graph, and replaying a dump's events and samples into a fresh one gives the same buckets and walks as
  the live one held.
  Check: a ledger test records a two-walk run to a dump with a ledger attached, replays the file into a
  second ledger, and compares them.
- [x] Wall time is kept in buckets of one fixed width over a bounded history: per bucket, each node's
  exclusive time, the rows each lane finished, the time between rows that no probe covers, each store's
  bytes held against its limit, the recomputations and seeks, and the worst lateness sampled. A span
  longer than a bucket is spread over the buckets it covers.
  Check: a ledger test feeds a hand-built span of three buckets' length and reads a third of it in each;
  and feeds more buckets than the history and reads the bound.
- [x] Each walk is one record: its lane, range, start and end, the plan it ran under, and per node what
  ran, by kind and by demand, with the time and bytes; a restart closes one record and opens the next, and
  the runs between a restart and its first row are the new walk's.
  Check: a ledger test walks, changes a param, walks again, and reads two records whose second holds
  only the changed node's runs and all of them.
- [x] A walk's record says how cold it was: per node, the rows that ran, the rows a store held and the
  rows a served file answered, so a rate is never read without what it was a rate of.
  Check: a ledger test walks a window cold, walks it again, then walks one overlapping it by half, and
  reads all ran, all held, and half of each.
- [x] A computation or decode of a key and row a store had discarded is counted as a recomputation
  against that store, in the walk and the bucket it happened in.
  Check: a ledger test walks a window twice over a memo that holds half of it and reads the second walk
  recomputing every row, the first walk's discards and its own, an LRU discarding the half the first
  left held before the second reaches it, and none on a memo that holds it; the graph test over a real
  decoder reads a decode of a row its cache had discarded against the cache, and the seeks. The check
  was reworded 2026-11-12, on Kendrick's word, from one that expected only the first walk's discards.
- [x] A walk's record keeps each node's cost in order along the range, coarsely, so a cost that grows
  with the rows is told from one that is flat.
  Check: a ledger test steps a tool whose cost doubles over the range and reads a last part several times
  the first, and a flat tool's parts equal within noise.
- [x] What a reader on another thread is handed is a copy it may hold while the stream continues, and
  taking it costs the emitting thread no wait longer than a bucket's bookkeeping.
  Check: a ledger test feeds from one thread while another takes views in a loop, with no error and the
  final view equal to a view taken after the feeder stopped.
- [x] A walk that finished no row before the next began leaves no record. Added 2026-11-12: the ladder
  begins the window walk at every change, so a drag opened a record a sync and pushed every walk
  before it out of the bounded history, the one a detector would compare the next walk with included.
  Reasoned from the ladder, not watched in the player.
  Check: a ledger test begins twice with no row between and reads one record, the second's.

## The catalogue and its simulations

Assumes: The ledger.

A class of trouble enters the catalogue with a detector and a simulation together, and the simulation is
the detector's proof in both directions.

Facts to weigh. The classes below have each been met and measured by hand: work nothing reads, in the
finding of 2026-11-12; a store discarding what the next walk recomputes, in 2026-10-31 and 2026-11-08; a
chain node run whole at every emit, its cost growing with the range, in 2026-11-08's second half; the
walk's cursor seeking, which the decoder's docstring is written to avoid; and the GUI thread's turn, the
unprobed residual no finding has yet taken apart, which has its own deliverable below. A static node charged per row, 2026-11-09's fault, is not
among them: since static is inherited in the plan, the fault is a tool that should declare STATIC and does
not, which the stream cannot tell from a tool whose output differs by row without comparing outputs.
`time.thread_time` ticks at the scheduler quantum on Windows, so a wait is a sum over many events or it is
nothing. The finding's own table shows a decode's wall well above the worker's CPU for a reason that is no
fault, the decoder's own threads. A walk driven by hand, as `bench.py` and the experiments under
`docs/findings/experiments/` drive theirs, emits progress and no begin; the ledger then opens a record at
the first progress, without the runs before it and without the range's first row, so a script whose
record is read calls `Graph.began` as the worker does. A walk's wall is not comparable with another's: a
walk half held costs less a row than a cold one with nothing wrong, and a lane's wall holds the turns the
ladder gave the other lanes; what two walks under one plan have in common is each node's cost a run. The
sync's plan carries the pinned set and not the selection. A served reader has one cursor, where the plate's
decoder keeps a second for the scrub, so a scrub of a served node during a walk makes the walk seek on it:
`docs/findings/2026-11-12-served-scrub-moves-the-walks-cursor.md`, where the seeks class surfaced it. It is
a fault of the player's and no false sighting; the healthy scrub below is on a live document.

Fork: whether a density folded for a node nothing shows is the same problem when the walk reaches the
node anyway. The class is built as work no watched node and no walked node asked for, with one threshold,
a named constant beside the detector. Observed on the purb document live and served, by the last box
below: where one threshold leaves the live walk silent and the served one flagged, it is one class; where
none does, the fold of a reached node becomes a second class with its own subject and threshold, so the
first can be set for the served case alone. Observed 2026-11-12, in the second half of
`docs/findings/2026-11-12-served-bake-upstream-walk.md`: one threshold separates them, so it is one class,
and the served walk's log then lists the folds of the nodes it reaches beside those it does not.

Fork: whether a class is quiet on healthy documents, which no simulation shows. Observed in Kendrick's
ordinary use, under the Worth a look below: a class that fires on a document with nothing wrong has its
threshold moved past what was seen, the sighting recorded beside the constant's finding; where no
threshold separates the healthy sighting from the simulation's, the class leaves the log and its figures
stay in the saved history.

Open: where simulations live and whether they are tests. Recommended, and what a session may build on:
one module under `sieve_player/dev/`, each simulation runnable by name from the command line, and one test
that runs them all. Since 2026-11-12, on Kendrick's word, the tests that run a simulation carry the
`simulation` marker and are out of the default run, their faults being built of wall time: one failed
once under a full suite with nothing wrong and not again alone. A check that names a simulation's test
is run with `pytest -m simulation`.

- [x] A problem is a value: its class, its subject, one line, its cost per row of the walk and as a share
  of it where it has one, the evidence the line was drawn from, and where in the code the class has come
  from before. A detector is a function from a ledger's view to problems and reads nothing else.
  Check: a catalogue test builds a view by hand for each class and reads the problem off it.
- [x] Each class has a simulation that builds the fault with the player's own Graph and Worker on a clip
  it writes for itself, needing no file of Kendrick's and no store of his. Run alone, it surfaces its
  class and no other.
  Check: one catalogue test per simulation, each asserting the set of classes surfaced is the one.
- [x] A healthy simulation, the same graph as the faults' with no fault, surfaces nothing; neither does a
  rewalk the memo holds, a walk beginning mid-clip, a scrub during a walk, or a bake behind one.
  Check: a catalogue test runs each and reads an empty log.
- [x] The classes present: work nothing reads; a store recomputing what it discarded, the memo, the plate
  decoder's cache and a served reader's each as their own subject; a node whose cost grows along the
  range; and the walk's cursor seeking. The worker waiting on the GUI thread is The GUI thread's turn's
  to add.
  Check: the simulations' test names each.
- [x] The log holds one entry per class and subject: a problem seen again updates its entry's cost and
  count and does not add one, an entry whose problem is no longer found says so and stays, and the
  entries order by cost. A walk with five faults at once is five entries.
  Check: a catalogue test feeds the same fault over ten walks and reads one entry counting ten, then a
  clean walk and reads the entry cleared and present.
- [x] An entry gives one block of text sufficient to begin on the fault without the session it was seen
  in: the class and the line, the figures and the evidence, the walk's lane, range and per-node table, the
  plan's lines for the subject and what it reads and is read by, the document itself as it would be
  saved, the video's path, the decoder's facts and the stores' limits, the commit, the dump's path when
  one is being written, the simulation that builds the same class, and the place in the code the class
  has come from.
  Check: a catalogue test takes the text for the served-bake simulation's entry, finds in it each of
  those by its label and the nodes the fault names, and loads the document back out of it.
- [x] A walk that costs more a row than the last walk of the same lane under the same plan, past a
  threshold, is a problem of its own class whatever the cause, its evidence the nodes whose cost moved
  and by how much; a walk under a changed plan is compared with nothing.
  Check: a simulation runs one plan twice with a tool made slower between, and surfaces the class naming
  the tool; a catalogue test changes a param between two walks and reads nothing.
- [x] With no entry at all, the ledger's recent history, the plan and the document can be written to
  one file that replays into a ledger, so a slowdown of no known class is handed over as it happened.
  Check: a ledger test saves, replays the file, and reads the same buckets and walks back.
- [x] `video-tests/purb-settings.json`, its bake served on a fresh graph, surfaces work nothing reads,
  naming crop and rescale, at a cost that agrees with the finding's table; the same document live
  surfaces nothing.
  Check: the finding's experiment, extended to attach a ledger and print the log; it is run by hand, the
  clip being Kendrick's, and its output is recorded as a second half of the finding.
- [x] The slower-than-last-walk class sees a walk slowed in the time no span covers. Added 2026-11-12 on
  building it: the class is built on each node's cost a run, in what ran in both walks, the wall of a
  walk being comparable with no other's, and so read nothing in a walk slowed between its spans, by the
  GUI thread's turn or a wait the probe does not time. A walk's record keeps its unprobed time, and the
  class compares it a row under the subject "unprobed".
  Check: a simulation holds the worker between rows for the second of two walks under one plan and
  surfaces the class, alone.

Worth a look: the thresholds, each a named constant beside its detector, against the purb and GoPro
documents in ordinary use for a session; a class that fires on a healthy document is a wrong threshold or
a wrong class, and which is his to say.

## What the trace costs

Assumes: The ledger.

Whether the ledger runs from the moment a video opens or only under an open window is decided by what it
costs the walk, and that is not known.

Facts to weigh. With `on_event` unset the probe yields and returns, and an unwatched graph pays the
demand's context manager at each entry and nothing else. `bench.py` times a cold fill bare and with a dump
attached, on one fill, which `docs/findings/2026-11-12-probe-cost-with-the-stream-facts.md` found too few
to read; the dump's first writer cost the walk through GIL handoffs rather than through its own work, the
message of efd1fe10 and `Dump`'s docstring say, so a consumer's cost is not its CPU time. The new facts add
fields to every event and a payload to every progress event once anything consumes the stream; the hits
are counted and the payloads built only then.

- [x] The walk's rate is measured on Kendrick's footage with nothing attached, with the new facts
  emitted to no consumer, and with the ledger attached, and stated as a finding beside the dump's
  figures. Split 2026-11-12 on Kendrick's word: the box also asked for the window open at each of its
  sizes, which this deliverable does not assume, and that half is a box under The window.
  Check: an experiment under `docs/findings/experiments/` and its finding.

Fork: whether the ledger is attached for the life of a video or of the window. Until the finding is in,
a session builds the window-lifetime attachment and nothing that forecloses the other. Observed in the
finding: where the walk's rate with the ledger attached sits inside the run-to-run spread of the rate
with nothing attached, the ledger is attached when a video opens and the window finds its history
waiting; where it sits outside, the attachment stays the window's, and the cost is stated in the window
itself beside the monitor's own band. On either side the figure on the player attaches nothing. Observed
2026-11-12, in `docs/findings/2026-11-12-what-the-trace-costs.md`: inside, at every point of the spread,
so the ledger is attached when a video opens. The finding says how little the criterion asked, the
spread being many times the cost, and that a walk long enough to pass the memo's limit was not measured.

## The GUI thread's turn

Assumes: The ledger.

A slowdown that is felt is a late frame or a dragging handle before it is a slow walk, and those are the
GUI thread's, which the stream does not see.

Facts to weigh. `window.Lateness` says how long the GUI thread went without turning its loop and nothing
of what held it, and exists only under a dump. `qt_trace.watchdog` dumps every thread's stack, at a hang
of seconds. The worker's signals land on the GUI thread as queued slots: `rowReady` per scrub,
`walked` and `clipWalked` per row, `seriesReady`, `densityReady` and `clipReady` per emit, each ending in
a repaint of the frame, the plot or the strip. The old monitor's unprobed line names "the GUI's turn"
among four things it cannot separate. The worker's own spans carry wall and CPU, and the two part for two
reasons the stream does not tell apart: waiting for the GIL, and a decoder's threads working. Added
2026-11-12 on building it: the pane has no paint of its own, its children being Qt's widgets painted
with no Python run, so a span around its paint event would time an empty background and it has none;
what its children cost the GUI thread is in the lateness and under no span. The monitor's paint is The
window's box for the monitor's own work. A wait lands in whatever span the worker is in, a fold as
readily as a tool, so a GUI thread holding the interpreter grows the folds' ms and with them the share
the work-nothing-reads class is judged by: the slot simulation with nothing pinned surfaced that class
on all four frame nodes beside its own, and pins them for it. The CPU clock's tick makes one span's wait
noise, so the sums are kept signed and a detector reads a walk's.

Fork: how fine the attribution is. It begins at one span per slot a worker signal lands in, named by the
signal, and one per paint of each of the player's top-level parts, the frame, the plot, the strip, the
canvas, the pane and the monitor. Observed on the purb document in the player, under the Worth a look
below: where those spans cover the time the lateness says the GUI thread was held, less than the largest
single span left over, the attribution stops there; where more is left uncovered than that, the part
holding the most is split one level finer, or the uncovered time is given its own span by what the loop
was doing, and the observation is made again.

- [x] The GUI thread's time is in the stream as spans on its own thread, each naming what it was: the
  slot a worker signal landed in, or the part that painted; the lateness is sampled into the ledger
  whenever one is attached, with or without a dump.
  Check: a window test, offscreen, walks a window and reads a span for each signal that fired and a paint
  span for the plot, on the GUI thread's name.
- [ ] The ledger keeps the GUI thread's spans in the same buckets as the worker's and apart from them,
  and the time view draws them as their own stack on the shared axis.
  Check: a monitor test feeds both threads' spans and reads two stacks.
- [x] How long the worker's spans spent off their own CPU is summed per bucket and per walk, read
  kinds apart from tool kinds, since a decode's wait is its own threads.
  Check: a ledger test feeds spans with wall above CPU and reads the sum, and reads none from decodes.
- [x] The worker waiting on a blocked GUI thread is a class in the catalogue: a walk in which the GUI
  thread's spans and the worker's tool-kind waits coincide past a threshold, its subject the GUI span
  that took the most, its simulation a slot made slow on purpose.
  Check: the simulation's test, and the healthy simulation still surfacing nothing.
- [x] The player attaches a ledger to each video's graph as it opens and drops it as the video closes,
  read or not. Added 2026-11-12: the fork of What the trace costs was observed on that side and no box
  held it, and the lateness of the first box has nowhere to go without one.
  Check: the window test of the first box reads the walk and its plan off the window's ledger, and
  none after the window closes. A lateness of the blocked GUI thread was read off it once, 2026-11-12,
  in that test before the read was dropped from it for the quarter second it slept.

Worth a look: the GUI stack on the purb document in the player against the offscreen figures of the
finding of 2026-11-12; the gap between the two is what this deliverable is for, and whether it closes is
a second half of that finding.

## The figure on the player

Assumes: nothing.

The one figure a user wants without opening anything is how fast the walk is going and how long the clip
will take, and the player is told both already.

Facts to weigh. The worker's `walked` and `clipWalked` signals reach the window per row with rows done and
rows in the range; a rate is two of them and a clock, with no consumer on the probe. `Header` is the
player's top bar and holds the walk's state. The old monitor's multiple is the cold projection, a
different number. Added 2026-11-12 on building it: a walk's beginning has no signal, so a lane's count
at or below its last is what opens a walk and the walk's first row is not in its rate; the clock is
the GUI thread's, so the rate holds the turns the ladder gave other work and how late the slot ran.
The memo's counters are every thread's and count a held row as one hit where a row that ran is a miss
a node, so they give no share of rows read from the GUI thread: the worker takes `Graph.tally` either
side of the walked row, and the two signals carry, of the rows done, those that ran and those that
read a bake. The video node and a served node go round the memo, so the tally holds the decoders'
reads their caches did not answer beside the memo's misses. A `peek` that misses from the GUI thread
between the two is counted with the row. A walk that read a bake is not cold by the second box's
sentence, and shows no time for the clip.

- [x] The player shows, on one control, the measured rate of the lane now walking as a multiple of
  realtime and the clip's length beside the time it takes or has left at that rate; idle, the last walk's.
  It reads the worker's own signals and attaches nothing to the probe.
  Check: a window test walks a window offscreen with `on_event` unset throughout and reads the control's
  text against the rows and the clock.
- [x] Beside the rate the control says what the walk was: cold, held in part and by how much, or served
  from a bake, read off the counters the memo, the decoder and a served reader already keep, across the
  walk. A rate from a walk that was not cold is not shown as the clip's time.
  Check: the same test walks a window cold, again, and one overlapping it by half, and reads the three
  labels; and reads no clip time beside the second and third.
- [x] Pressing it opens the monitor, the same window Dev opens.
  Check: the same test presses it and reads the window shown.
- [ ] The figure is the one the monitor's header leads with, by one definition both read.
  Check: a monitor test reads the two equal over a walk.
- [x] A walk is cold while no row of it read a bake and a store held no more than a named share of
  them. Added 2026-11-12 on building it: the display's row is computed on the scrub's rung before the
  walk reaches it, so a window never walked read 49 rows ran and 1 held, paused and under playback
  alike, and a cold that asked every row to have run showed a time for the clip on no walk.
  Check: `docs/findings/experiments/2026-11-12-the-figure-on-the-player.py`, whose first and fourth
  walks give a time for the clip and whose second and third, held whole and by half, give none.
- [x] The control is drawn and not written, Kendrick's word of 2026-11-12: the lane's glyph, the
  rate, one bar whose width is the range and whose filled part is the rows done, cut by what they
  were, and a time under the glyph of what it is; the words and the counts are its tooltip, which is
  the text the first box's check reads. The header's count of the clip walk's rows is the bar's.
  Check: the same experiment, handed a folder, grabs the header at each walk.

## The window

Assumes: The catalogue and its simulations.

If a slowdown is felt with the window open, where it came from is on screen as it scrolls past, how it
grew is readable back along the same axis, and what it is is one line with a button.

Facts to weigh. The old window is a drop-down of views over one scroll area, polled on a timer, each view
a painted widget sized for a snapshot; none has a time axis. `monitor_views.py` states the colour rule
this window keeps: hue is the product type's, the canvas's connector hue, never a node's, and unprobed is
the neutral gray; the plot's spec decided the same for series on 2026-11-10 and names its fallback. A
window opened from Dev is kept on the main window and outlives the menu action. The player's selection is
`Player.selection` and the pinned set is the document's; the two together are what is watched. A ledger
attached after the graph's last sync has seen no plan, and its walks carry none until the document next
changes; `Graph.sync()` on an unchanged document emits the plan again and moves nothing, the decoder's
`output` setter returning on an unchanged value and the memo and the readers keeping the same keys. The
dump's writer times itself into the file and passes nothing to `on_event`, so its span is not in the
stream, and the ledger passes over that kind so that a dump replays to what the live ledger held; the
ledger holds no graph to emit through.

The figure at the top is the player's, the measured rate of the lane now walking, by The figure on the
player. The cold projection is a different number, and the finding has the two at twice one another on
one walk; it is not drawn here until The old monitor goes has rebuilt it on the plan's reach.

The old monitor goes, Kendrick's word of 2026-11-12. Until the last deliverable it stays reachable under
its own Dev entry, since the window is not yet there to replace it.

Open: how a consumer's own cost enters the stream, which the monitor's-own-work box below needs and the
dump does not yet do. Recommended, and what a session may build on: the dump passes its span on down the
chain, `Stats` passing over the kind, and the ledger stops passing over it; whoever attaches the ledger
times its bookkeeping and the window its painting and detecting, and emits each as a span on the graph it
attached to, the ledger staying without one; and a span of the monitor's own is never itself timed, so
the monitor's band does not hold the cost of drawing the monitor's band.

Fork: which tracks earn their place. The tracks begin as the first box lists them. Observed by watching
each simulation shown, under the last-but-one box, and in Kendrick's use: a track on which some class was
read arriving stays in the default list; one on which none was leaves the default and stays addable.

- [ ] The window's default is time across: where the worker's time went, stacked by node in walk order in
  each node's type hue with unprobed in gray and idle empty, scrolling with the wall clock; under it on
  the same axis the cost of a row, each store's bytes held against its limit with a mark at each
  recomputation, and the GUI thread's lateness; the GUI thread's own stack joins them with The GUI
  thread's turn.
  Check: a monitor test feeds a ledger a walk whose second half costs twice its first and reads, off the
  painted image, a taller stack in the later columns and the row cost's line higher there.
- [ ] A node's band is told by pointing and by a name at the right edge where the band is tall enough to
  take one; no node has a colour of its own.
  Check: the same test hovers a column and reads the node and its figure in the tip.
- [ ] The axis holds more than the window is wide: it can be drawn out to the ledger's whole history and
  back in, and scrolled back along while the stream continues.
  Check: a monitor test feeds more history than the widget's width, draws out, and reads the first
  bucket's column.
- [ ] The log is beside the time view, each entry its line, its cost, how long since it was first and
  last seen, whether it still holds, and a button that puts the entry's text on the clipboard. A problem's
  first sighting is marked on the time axis at the moment it was seen.
  Check: a monitor test surfaces one problem, presses its button and reads the clipboard; and reads the
  mark's column.
- [ ] A problem's first sighting is one line on stderr in the player's log form, and nothing is printed
  for a sighting after the first.
  Check: a monitor test surfaces a problem over three walks and reads one line.
- [ ] The window goes full screen and back by a key and by a control, and holds together small: as it
  narrows the log moves under the time view, and as it shortens the tracks leave in a stated order, the
  lateness first and the stack last, until the header, the stack and the log's newest entries remain.
  Check: a monitor test sizes the window to a full-screen size and to the stated smallest and reads which
  parts are visible at each.
- [ ] The monitor's own work, its ledger's bookkeeping on the emitting thread and its painting and
  detecting on the GUI thread, is in the stream as spans under its own name and is drawn as a band like
  any other, as the dump's writer already is.
  Check: a monitor test runs the window over a walk and reads the monitor's band nonzero in the image
  and its spans in the ledger.
- [ ] A control writes the recent history to a file, the catalogue's hand-over for a slowdown with no
  entry, and puts the file's path on the clipboard.
  Check: a monitor test presses it and replays the file.
- [ ] The parts are a list: a track or a panel is added by adding one to it, and the window lays out what
  the list holds.
  Check: a monitor test adds a track that paints one colour and reads it in the image.
- [ ] A simulation run with its show flag opens this window on the simulation's graph and repeats the
  fault, so each class can be watched arriving.
  Check: a monitor test starts a simulation shown, offscreen, and reads its class in the window's log.
- [ ] The window watches whatever graph the player holds, through a video closing and another opening,
  and with no video says so.
  Check: a monitor test swaps the player's graph and reads the new walk's rows.
- [ ] A ledger attached to a graph already planned holds that plan from its first walk on. Added
  2026-11-12 on driving The ledger.
  Check: a monitor test opens the window on a synced graph, walks, and reads the plan on the walk's
  record.
- [ ] The selection is in the stream beside the pinned set, so a fold of the selected node is work a
  watched node asked for. Added 2026-11-12 on building The catalogue: the plan a sync carries holds the
  pinned set alone, and the work-nothing-reads class takes pinned for watched, so a node selected to
  look at its density reads as unwatched.
  Check: a monitor test selects a node whose fold the catalogue had surfaced, walks, and reads the entry
  cleared.
- [ ] The walk's rate is measured on Kendrick's footage with the ledger attached and the window open at
  each of its sizes, and stated in What the trace costs' finding beside the figures there. Split
  2026-11-12 from that deliverable's box, which asked it before the window existed.
  Check: that finding's experiment, extended to open the window, and a second half of the finding.

Worth a look: the window full screen on the second monitor through a session on the purb document and one
on the GoPro clip, bake live and served; and small beside the player.

## The old monitor goes

Assumes: The window.

Two accumulators over one stream are two answers to keep agreeing.

Facts to weigh. `summary` and `table` are imported by every experiment under `docs/findings/experiments/`
from 2026-11-08 on, each pinned in its finding to the commit it ran at. `tests/test_monitor.py` asserts the
old snapshot's arithmetic.

Fork: what becomes of an experiment that imports it. An experiment a box of this spec reruns, the
finding of 2026-11-12's, reads the ledger's table from then on; one no box reruns is left as the script
of the commit its finding names, and says so in its docstring's first line.

Kendrick's reading of 2026-11-12 is that a jump of the window to rows nothing holds is a cold walk taken
for free, and the best sample of how the clip will go. Four things stand between a cold window and the
clip, each seen in a finding or in the code: the window walk folds densities and the clip walk does not;
a walk's first rows pay a seek, a reader's opening and each static node's one run; a whole-run chain node
costs by the range, so six hundred rows say little of thirty-eight thousand; and what a row costs follows
what is in it, the blobs and tracks of that stretch of the clip.

Fork: whether a cold window predicts the clip. Observed on the purb document, as a finding: cold windows
taken at several places along the clip, each projected to the clip with the folds and the first rows left
out, beside a clip walk's measured time. Where the projections agree with the clip walk and with one
another inside the walks' own spread, the projection is one figure from the latest cold window; where
they agree with the clip walk only together, it is stated as the range the cold windows so far span, with
how many there were; where a whole-run node's growth is what separates them, the projection carries that
node's cost by its growth and not by its mean.

Fork: whether the cold projection is worth keeping at all. Observed once it sums only what the plan
reaches: where it agrees with the measured rate of a cold walk on the simulations and on the purb
document, it is drawn beside the measured rate and a disagreement past a threshold is a class in the
catalogue; where it does not agree on a healthy walk, it is not drawn, and the finding says by how much
it missed.

- [ ] The per-node table, a walk's shares and the cold projection, is a reading of the ledger, and the
  cold projection sums only the nodes the plan reaches.
  Check: a test switches a node to served after a live walk and reads a projection without the nodes
  behind it.
- [ ] Each node's cold cost is taken from the rows of it that ran, in whichever walk they ran, and the
  projection says which walk each node's figure is from; a node whose figure is from before the last
  change upstream of it is marked so.
  Check: a test walks cold, changes a param mid-chain, walks again, and reads the changed node's and its
  readers' figures from the second walk and the rest from the first, unmarked.
- [ ] A control empties the memo, the decoder's cache and every reader's and walks the window again, for
  a cold figure on demand; it says before it does that what is held will be recomputed.
  Check: a monitor test presses it and reads a walk whose every row ran.
- [ ] `Monitor`, `MonitorWindow` and `monitor_views.py` are gone and nothing imports them.
  Check: the seams test.

## Non-goals

The fault itself. Whether the window walk folds a density for a node behind a served bake, or for any node
nothing shows, is a decision about the walk and is made elsewhere; this branch leaves the walk as it is and
is judged by whether it says so.

What a bake would buy at each wire. The saving is the cost of the nodes only that wire reaches, which
the ledger and the plan hold; the cost is a served read, and the two measured so far, in the findings of
2026-11-08 and 2026-11-12, are not proportional to their pixels, so there is no model to subtract. The
monitor says when a bake is not paying; where one would is a later spec's, after a finding on the read.

An overlay on the canvas's nodes and wires. It reads the ledger and the log and wants this branch's
window looked at first.

Problems that are not costs: a stale bake, an unfed node, a tool that raised. A node's standing says
those already.

Detection of a tool that is static in fact and undeclared. It needs outputs compared, which the stream
does not carry and should not.
