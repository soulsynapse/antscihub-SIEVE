# What a memo of references holds

2026-11-15, on v5-memo-holds-no-view. Experiment:
`docs/findings/experiments/2026-11-15-what-a-memo-of-references-holds.py`, run three times, a
process each, on `video-tests/00000_168-178.mp4`, 1920x1080, with
`00000_168-178.shapes.geometry.json`. It answers docs/spec/memo-holds-no-view.md's What it costs in
part; what it leaves is at the end.

The plan is video -> region with no shape chosen -> rescale at 1.0 -> gray, 200 rows walked from
row 0 by `Graph.compute` on gray, the memo and the plate's cache at 2048 MB each. Three ways of
holding a result that is another store's array: by reference, as the tree now does; as the run
handed it, which is what the memo did before; and as a copy of its own, which is what the spec
first said.

| held | ms a row | region, ms a run | rescale, ms a run | memo, MB | memo's discards | rows of 200 answered without a run: region, rescale, gray | the process grew, MB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| by reference | 1.49 | 0.059 | 0.019 | 396 | 0 | 200, 200, 200 | 1616 |
| as handed | 1.49 | 0.047 | 0.020 | 2043 | 157 | 147, 148, 148 | 1513 |
| as copies | 3.37 | 0.927 | 0.991 | 2043 | 157 | 147, 148, 148 | 3263 |

The cache held 1187 MB in all three, every frame of the 200. The video's decode was 0.66 to 0.74 ms
a run and gray's 0.63 to 0.68.

Held as handed, the memo counted the frame three times over, once under region, once under rescale
and never as its own, filled its limit at row 148 or so and discarded 157 planes, 52 of them gray's,
which were the only ones it owned: the process held 100 MB less than by reference for having thrown
away results it then had to compute again. Held by reference the memo counts gray's 396 MB and two
references a row, discards nothing, and every row of every node is answered without a run. The walk
takes the same time either way.

Held as copies the count is as true as by reference and costs 0.9 ms a run of each passing node,
more than the decode of the frame copied, 1.9 ms of the row's 3.4, and 1.65 GB more of the process
for two copies of what the cache holds; the memo fills and discards as it did when it miscounted.

A first run of the experiment found region's result held as a copy by the reference rule as first
written: `np.ascontiguousarray(f[y0:y1, x0:x1])` over the whole plate is the frame's buffer, shape
and strides under another array object, and a test of `v is a` missed it. `graph._same` now takes
the two for one array.

Not read here, and still the spec's: the monitor's report on a walk in the player, with the
window's need of the memo, the stores under MACHINE against SIEVE's memory, and the rows of a
window's history the memo keeps; the plan the report of 5.9 GB was made on, which this plan stands
in for. Not run: a served region above the passing nodes, a strip, a table.
