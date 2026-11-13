# A cold window does not predict the clip while a chain node runs whole

2026-11-12, on v5-monitor, the working tree over 5ceb287a. The observation the two forks of The old monitor
goes in `docs/spec/monitor.md` ask for. Experiment:
`docs/findings/experiments/2026-11-12-a-cold-window-and-the-clip.py`.

Five windows, each over rows nothing held, at 0, 20, 40, 60 and 80% of the clip, each projected to the
clip by `catalogue.cold`: every node the plan reaches at its ms a row under the walk's own demand, its folds
and seeks left out, a static node at nothing, and the walk's unprobed ms a row. Then the clip walked cold on
a fresh graph and read off its record. `video-tests/purb-settings.json` as it stood that evening, 38100
rows, windows of 600, the chain emitting every 30; and the simulations' graph, 64 rows, windows of 12.

The first run was made while Kendrick ran a bake and a walk in a player on the same machine; the second,
of the saved document alone, with less beside it. `size` ran whole in both.

| | projected, ms a row | the clip walk, ms a row | projected over measured |
| --- | --- | --- | --- |
| simulations, twice | 2.42 to 2.74, 2.30 to 2.68 | 2.50, 2.46 | 0.97 to 1.10, 0.93 to 1.09 |
| purb, every bake live, beside a bake | 2.07 to 3.66 | 5.84, 222 s | 0.35 to 0.63 |
| purb as saved, beside a bake | 0.18 to 1.54 | 3.03, 116 s | 0.06 to 0.51 |
| purb as saved, quieter | 0.17 to 1.32 | 1.91, 73 s | 0.09 to 0.69 |

What separates them on purb is one node. `size` had a `run` and no `step`, so the plan ran it whole over
the rows so far at every emit: 0.02 to 0.07 ms a row inside a window of 600 and 2.73, 2.53 and 1.55 ms a
row over the clip in the three runs, between a half and four fifths of the clip walk. `count` is the same
shape at a fiftieth of the cost. The catalogue read the quieter clip walk as `grows size`, 68% of it,
82 ms a run at the range's end against 11 at its start, and nothing else. The frame nodes did not part:
the video's decode was 1.03 to 1.53 ms a row across the live windows and 1.42 over the clip, crop 0.23 to
0.48 and 0.35, blobs 0.29 to 0.63 and 0.57, which is what a row's content does and is also what the
contention did to both alike.

With `size` and `count` carried by their growth, an emit's ms fitted against the rows it ran over along
the window and summed over the clip's emits (`Projection.ms_row(rows)`), the projection over the measured
was 0.40 to 1.24 beside the bake live, 0.53 to 0.97 beside it saved, and 0.81 to 1.49 quieter. In the
quieter run `size` alone came to 1.37 to 1.61 by growth against 1.55 measured. The window at row 0 is the
one over, in both saved runs, by its unprobed: 1.17 and 1.39 ms a row where the other four read 0.06, a
second or so in no span on the first walk of a served series head, its file read whole.

So, for the first fork: a whole-run node's growth is what separates a cold window from the clip, and the
projection carries such a node by its growth. Carried so, five windows still span a factor of two, of which
the first window's opening and the rows' content are each a part and the machine a third; on this evidence
it is a range and not a figure.

For the second fork, whether the projection is worth drawing: on the simulations it agrees with a cold
walk's measured rate inside a tenth. On purb it did not, and purb's clip walk was not a healthy one, the
catalogue naming the reason. Neither side of the fork as written is met, and it is left untaken.

`size` was given a `step` the same evening, on Kendrick's word, held to its `run` by `tests/stepping.py`'s
oracle in `tests/test_size.py`; the plan then steps it on purb, and `count` still runs whole. A run of both
purb cases with it was started and its figures are not in this finding: they are what the second fork
wants, a clip walk with no known fault beside its windows' projections.

Not observed: a machine left alone; the GoPro document; a window of another length, the fit of a growth
over 600 rows being carried sixty times past them; a clip long enough for the memo to pass its limit, which
this one's frame nodes do within the walk and the record shows no recomputation for, the clip walk reading
each row once.
