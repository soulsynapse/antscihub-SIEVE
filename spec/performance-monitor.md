# The performance monitor

Three things, kept apart. A probe at the one call site where tools run emits each timing as it
happens and knows nothing else. A live display reads what the probe has accumulated and shows
it when asked, in the form Blender's node editor uses for its Timings overlay: the number on the
node, off by default. A recorder, later and its own branch, subscribes to the same probe and
writes every event down, as the pane Houdini calls its performance monitor does; the display never knows it is
there and it never knows the display. The probe and the display are this branch. The module to
read before touching this is `sieve_player/graph.py`, the run call in `_compute`; `bench.py` is the
headless reader of the same numbers, and the decoder already keeps step and seek means the probe
sits beside.

## Probe

Assumes: nothing new; the decoder and memo counters as they stand.

- [ ] Every run of a tool, and the video node's read, emits one event, node, row and wall ms,
  exclusive of the nodes it reads:
  a cold scrub row charges the decode to the video node and gray's work to gray, not to the node
  that asked for them. A tool is not changed and does not see the clock. The event goes to one
  callable on the graph, unset by default, so a later reader is a consumer and not a reopening of
  the call site.
  Check: a test runs a two-node graph whose tools wait a known time, catches the events, and
  asserts the reader's figure is less than the pair's together and that each node emitted once per
  row.
- [ ] The first consumer keeps, per node, the last figure and a running mean over the window the
  decoder uses; beside them the series chain's time per emit and the walk's rate in rows per
  second, with the decoder's step and seek means and counts and the memo's and the decoder cache's
  bytes and hit rate.
  Check: a test walks a short window and asserts every counter has counted; no test asserts what
  a timing reads.
- [ ] The numbers leave the runtime as one plain snapshot taken under the graph's lock, the way
  results leave the worker, so the window and `bench.py` read the same thing and neither reaches
  into the graph's state.
  Check: `tests/test_seams.py` still passes; `bench.py` prints the snapshot as a table after its
  timings, nodes sorted by mean.

## Timings toggle

Assumes: Probe.

- [ ] A gauge button in the canvas's top left corner, Tabler's gauge glyph beside the others in
  `sieve_player/glyphs`, drawn the way the column's buttons are and lit while on; a key stands in
  for it as a key does for each of them. It is a mode and not an action, which is why it sits
  apart from the column of actions at the top right. Off by default and not stored in the
  document; off, nothing the user sees changes from today. It is there rather than in a menu
  because performance is a first thing about this player, now and later, and a recorder's button
  has its place beside it.
  Check: Kendrick looks, with it off, and finds nothing new but the one dim glyph.
- [ ] On, each node on the canvas draws its last and mean ms under its body, as Blender draws a
  geometry node's time; the figures reach the canvas as a node-to-figures dict through the window,
  the way params do, so the canvas still never names the runtime. They are refreshed as the walk
  reports, at the series emit cadence, not per row.
  Check: Kendrick looks: dragging a threshold moves that node's figure and no other's; a cold
  scrub does not inflate the last node's figure.
- [ ] On, a corner of the display carries the globals as Blender's Statistics overlay does: walk
  rate against the file's fps, step and seek ms with counts, memo and cache MB and hit rate.
  Check: Kendrick looks: on the 5K file the step and seek figures agree with the decoder commit's
  measurement to the order of magnitude, and the corner says whether the walk is at rate.

## Not now

Each of these is wanted and left out so the branch has an end. None is a judgement against the
thing itself.

- The recorder: the next branch. Record start and stop, every probe event written down with its
  row, self and total time per node, a sortable view, Houdini's shape. It assumes the probe's
  event callable and nothing of the display, which is why the callable is on this branch.
- A history or chart of timings in the live display. The live figure stays a last and a mean
  because the bursty case, a scrub's seek, is the recorder's job, not a second statistic here.
- The latency from `goto` to the frame on screen, or any GUI-thread timing (to_qimage, the heat
  LUT, the pane redraw). The felt number, and it stamps the display path with a clock that every
  later change there has to carry, and the probe's numbers first say whether the time is there at
  all.
- A profiler, flame graph, or memory profiler. When a node's number is surprising, cProfile on
  `bench.py` is the next tool.
- A preference that persists the toggle, or a log written by the display. A number worth keeping
  goes in a commit message or a finding, read off the screen, until the recorder writes it.
