# The performance monitor

Three things, kept apart. A probe at the sites where work is done and where it is discarded emits
each fact as it happens and knows nothing else. A recorder, later and its own branch, subscribes to
the probe and derives from what it wrote down, as the pane Houdini calls its performance monitor
does. A live display, also later and its own spec, reads what a consumer has accumulated and shows
it, in the form Blender's node editor uses for its Timings overlay. This branch is the probe, and
the proof that its stream is enough for a recorder: every event written to a file as it arrives,
and tests that read the file back and derive from it the things a recorder exists to derive. The
display is written off that recording, not off the snapshot's field list, which is why it waits.
The module to read before touching this is `sieve_player/graph.py`, `probe()` and the run call in
`_compute`; `bench.py` is the headless reader of the same numbers.

The probe's rule, and what bounds it: an event carries what only its site knows and costs nothing
to read there. Anything a reader can derive from the stream, a redecode, a seek's distance, a
recompute after eviction, what one drag cost, is the reader's to derive and never the probe's to
detect. A number on a screen is a comparison against something, the other nodes on the canvas,
the file's frame budget, the same file on an earlier run, and which something is a question for
the display and the recorder, so nothing here chooses one. Nothing on this branch detects anything
and nothing on this branch is drawn.

## Probe

Assumes: nothing new of the decoder and memo but the counters named below.

- [x] Every run of a tool, and the video node's read, emits one event: node, row, the node's raw
  key, a kind, the result's bytes, and wall ms exclusive of the nodes it reads: a cold scrub row
  charges the decode to the video node and gray's work to gray, not to the node that asked for
  them. The kind is what the site knew for free: for a read, whether the decoder's cache answered,
  stepped, or sought, read off the decoder's own counters either side of the call; for a tool,
  that it ran, since a memo hit is not a run and emits nothing. A tool is not changed and does not
  see the clock. The event goes to one callable on the graph, unset by default, so a later reader
  is a consumer and not a reopening of the call site.
  Check: a test runs a two-node graph whose tools wait a known time, catches the events, and
  asserts the reader's figure is less than the pair's together, that each node emitted once per
  row, and that a cached read's kind says so.
- [x] A graph change is a boundary in the same stream: `sync()` emits one event of its own kind,
  with no row and no time, so a reader can say what one drag cost. This bends the rule above, a
  sync being no run, and is the one bend: the callable carries runs and the boundaries between
  them, nothing else.
  Check: a test syncs and finds the boundary between the runs before and after.
- [x] The first consumer keeps, per node, the last figure and a running mean over the window the
  decoder uses, and ignores key, kind and bytes; beside them the series chain's time per emit and
  the walk's rate in rows per second, with the decoder's step and seek means and counts, the
  memo's and the decoder cache's bytes and hit rate, and the memo's evictions, the one count the
  stream cannot reconstruct.
  Check: a test walks a short window and asserts every counter has counted; no test asserts what
  a timing reads.
- [x] The numbers leave the runtime as one plain snapshot taken under a lock, the way results leave
  the worker, so the window and `bench.py` read the same thing and neither reaches into the graph's
  state.
  Check: `tests/test_seams.py` still passes; `bench.py` prints the snapshot as a table after its
  timings, nodes sorted by mean.

## Stream

Assumes: Probe. The boxes land in this order; the first on its own commit before any field is
added, since the fields below triple the event's width.

- [x] The event is a record with named fields, not a positional tuple. Every consumer, Stats, the
  dump below and the tests, reads fields by name, so a field added later fails nowhere silently.
  The six fields the probe already carries keep their names and meanings.
  Check: Stats and the probe tests read by name; a test builds an event with one field missing
  and the consumers refuse it rather than misread it.
- [x] Each event also carries its start as a timestamp on the clock the probe already reads, the
  emitting thread's name, and the thread's CPU ms beside the wall ms, all read at the site where
  the wall time already is. A reader orders events across threads from the timestamp, sees two
  runs overlap, and reads wall far above CPU as a run that waited, on IO, the GIL or a lock,
  without the stream saying which.
  Check: a test runs tools on two threads, reads the events back, and finds the overlap from
  timestamps and durations alone; a tool that sleeps shows CPU ms well under wall ms.
- [x] Each event says what it served: the scrub or the walk. The worker knows this at the top of
  each loop and sets it on the thread, in the same thread-local the probe keeps its stack, before
  computing; the probe reads it. Rows that reach the stream from outside the worker, `bench.py`
  and the tests, carry neither. The earlier plan to infer this from the row sequence is withdrawn:
  it is a value the site has, and the rule gives it to the probe.
  Check: a test asks the worker for a display row during a walk and finds the scrub's events
  marked as such among the walk's.
- [x] Two new kinds from the sites where work is discarded: an eviction from the memo and an
  eviction from the decoder cache, each with the node or row it dropped and the bytes freed, so a
  reader can draw either store's size over time or over rows walked, and can tell a redecode
  forced by eviction from one that was not. Both stores reach the same callable through the graph
  that owns them. The intro's "one call site" is now three, and the Probe section's "one count the
  stream cannot reconstruct" no longer holds; the memo's counter stays for the snapshot.
  Check: the walk test that forces an eviction finds the eviction event, with bytes equal to the
  memo's change, and the sum of every entry's bytes less every eviction's equals the memo's bytes
  at the end.
- [x] The walk's progress is an event of its own kind, rows done and rows in the window, emitted
  by whoever drives the walk, the worker and `bench.py`, through the same callable. Stats consumes
  it from the stream and `walked()` goes, so there is one route for the fact and one entry point
  on Stats, `event`.
  Check: `bench.py` and the walk test no longer call `walked()`; the rate in the snapshot still
  reads.
- [x] The sync boundary carries the new plan's node-to-key map. `sync()` already computes every
  key, so this costs nothing; a reader derives which nodes a drag changed as the nodes whose key
  differs from the previous boundary's, and the window never has to say what it edited.
  Check: a test changes one param, syncs, reads the two boundaries back, and derives that node
  changed and no other.
- [x] The dump: a consumer that writes every event as one JSON line, appended as it arrives, with
  a header line first carrying what a reader needs that no event has: the file's path, fps, row
  count and frame size, and the memo's and cache's limits. One line per event means a file closed
  by a crash reads back to its last complete line. A separate function converts a dump to the
  Chrome trace event format, one complete event per run with its thread as the lane and the other
  fields as args, so Perfetto or chrome://tracing shows the timeline, self and total time per node
  and the idle on each thread without a viewer of this repo's. The dump writes on the emitting
  thread through a buffered file until the overhead line below says otherwise.
  Check: tests write a short walk with a param change in it and read the dump back, deriving from
  the file and not from in-memory events: the redecodes as two uncached reads of one row, the
  recomputes as one key and row run twice, what the change cost as the per-node means between
  the two boundaries, and the walk's rate from the progress events. The conversion of that dump
  parses as JSON and every event in it has a timestamp, a duration and a thread. A dump truncated
  mid-line reads back to the line before.
- [ ] Two process samples, in the dump and not in the probe, since both measure rather than carry:
  the process's resident memory, read once at each progress event, so a process growing while
  memo plus cache stays flat says something is held that neither store knows of; and the GUI
  thread's lateness, a timer the window runs only while a dump is attached, which emits how late
  it fired, so a reader sees when the main thread was blocked and for how long without a clock in
  the display path. The lateness sampler is the one piece of this branch that touches the window,
  and it draws nothing.
  Check: a test attaches a dump, blocks the GUI thread for a known time, and finds a lateness
  event at least that long; the walk test finds a resident-memory figure on each progress event.
- [ ] The probe is cheaper than what it measures, and `bench.py` says by how much: its fill runs
  once with the callable unset and once with the dump attached, and prints both, and the dump's
  file size for the run. The two figures are a measurement, so they live in a commit message or a
  finding, never here; the standard is that the difference stays within the run-to-run noise the
  bench already shows between its first and second fill.
  Check: `bench.py` prints the three figures; the finding for this branch records them.

## Not now

Each of these is wanted and left out so the branch has an end. None is a judgement against the
thing itself, and this list is a scope, not a prohibition.

- The display: a gauge toggle at the canvas's top left, a figure under each node, a corner of
  globals. Its own spec, written from the questions a user asks of a running player, which node
  costs what, what a row costs through the chain and whether the walk will finish before playback
  reaches it, how much memory is held, whether a felt lag is the worker's, and written after a
  dump of a real session shows which figures move under which actions. A bare ms or MB answers
  none of those; each figure on screen is a comparison against a named reference, and choosing
  the references is that spec's first job. The video node's mean, as a single figure, mixes a step
  and a seek, two populations an order apart on large footage, and that spec decides how it is
  shown or whether it is.
- The recorder: the reader of dumps. Start and stop in the player, self and total time per node,
  a sortable view, memo growth and store size over rows walked, slowing over a session, the cost
  of each boundary, the chain's floor against the wall rate, time to finish for a stated length
  of footage, and comparison of one run against another. The last needs a notion of which events
  correspond across sessions, and node ids are per document and keys change with params, so it
  probably lines up on per-node means and the chain's per-row cost rather than on events; that is
  the deliberation before its spec, not before this one.
- The latency from `goto` to the frame on screen, and any clock in the display path: to_qimage,
  the heat LUT, the pane redraw. The lateness sampler localises a blocked main thread in time, not
  in code; when a dump shows the main thread late while the worker's figures are small, that is
  the case for a clock in the display path, and it is made then.
- A history or chart in the live display, a profiler, a flame graph, a memory profiler. When a
  node's number is surprising, py-spy or cProfile on `bench.py` is the next tool.
- Needless copies inside a tool, unreleased references, and whether a serial tool could legally
  be chunked. No stream from a call site carries these: bytes is the result's size and not the
  tool's allocations, a leak's owner is tracemalloc's to name, and a row's dependence on the row
  before is the tool's contract. The stream shows the serial shape and the idle, and stops there.
- A preference that persists anything, or a log written by anything but the dump. A number worth
  keeping goes in a finding, read off a dump.
