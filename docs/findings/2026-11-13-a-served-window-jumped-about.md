# A served window has no frame ready: a drag of its playhead shows nothing, and every move is a seek

2026-11-13, on v5-held over 20d1998c with the held-results work in the working tree, on an i9-14900KF,
by `docs/findings/experiments/2026-11-13-a-served-window-jumped-about.py`, offscreen. Kendrick had a
bare walk running on the machine throughout, so each figure is against its neighbour of the same run
and none is the machine's best. The document is a copy of `video-tests/test.json`,
`rep3_intermittent_crop.MP4` at 462 by 456 and 59.94 fps, 30579 rows, video shown, coarsegrain, motion,
reduce and smooth; its held file is Kendrick's own of that afternoon, one run over the whole clip,
restamped under the tool files as they stood. With that run held every window is served, and with no
frame node in the plot none of its rows is walked (`window._ask_window`, `_idle`).

Five windows of 300 rows placed about the clip, six moves of the playhead inside each, then a drag over
60 rows and two seconds of play; once with the run held, once with it let go, on rows the first pass
had read none of:

| | served | walked |
|---|---|---|
| `set_window` on the GUI thread, median and max | 0.40, 0.46 ms | 0.22, 0.29 ms |
| the first frame after a placing | 8.9, 37.6 ms | 8.1, 18.4 ms |
| the window's rows walked after it | none walked | 359, 444 ms |
| a frame after a move of the playhead | 12.3, 21.5 ms | 0.00, 0.00 ms |
| rows a drag over 60 showed | 0 | 60 |
| rows shown in 2 s of play, of 120 ticked | 117 | 117 |

What the held runs cost the GUI thread at a placing, the cut from the run, the strip's stretches and
the card's size line together, is under half a millisecond and is not what is felt.

A drag's rows are guesses (`window.seek` with `commit=False`), which `goto` serves from the memo or not
at all. A walked window has every row in the memo some 360 ms after it is placed and a drag shows each;
a served one has none, so the frame stands still until the button is let go. A committed move in a
served window is a seek and a decode on the scrub cursor each time, 12 ms on this clip. Play keeps up
here, each tick a sequential read.

Everything above is of the tree before the change below.

## Since, the same evening

A served window's frames are walked as a walked window's are, the chain alone spared: `_idle` and what
hung from it are gone from `window.py` and `worker.py`. The same script, the same document and run,
no bare walk beside it this time, so these are against each other and not against the table above:

| | served | walked |
|---|---|---|
| `set_window` on the GUI thread, median and max | 0.32, 0.34 ms | 0.21, 0.33 ms |
| the first frame after a placing | 7.5, 45.0 ms | 7.5, 17.7 ms |
| the window's rows walked after it | 332, 358 ms | 347, 399 ms |
| a frame after a move of the playhead | 0.00, 0.00 ms | 0.00, 0.00 ms |
| rows a drag over 60 showed | 60 | 60 |
| rows shown in 2 s of play, of 120 ticked | 117 | 117 |

The frames' walk is the same third of a second either way on this document, whose chain is cheap; what
serving saves is the chain's steps, which this script does not time.

Not measured, then or since: a clip whose frames cost more. `GX010047c2_02_17_26.MP4` is 5312 by 2988;
before the change a move in a served window of it was expected to cost what a seek there does, and
since it a served window of it is expected to take as long to fill as a walked one's frames do. Both
are extrapolation.
