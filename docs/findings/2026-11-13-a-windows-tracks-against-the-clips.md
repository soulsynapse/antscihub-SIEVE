# A window's tracks against the clip's, over the rows both reach

2026-11-13, on v5-held at 20d1998c. Experiment:
`docs/findings/experiments/2026-11-13-a-windows-tracks-against-the-clips.py`, run three times, the
document's `merge_ratio` of 0 and then 1.5 and 3. The Fork of Which results are the same result in
`docs/spec/held-results.md` as it stood at a7ceace5, since rewritten without it, asks how far a window walk's result is from the clip walk's at the same rows.

`video-tests/purb-168-178.json`, 590 rows at 59.94 fps, 18.8 records a row and 22 at most, `track` at
`lost_rows` 30 and `min_rows` 3. The blobs tables are computed once; `track` is stepped from row 0 and
again from each of 22 window starts, every 25 rows, with `travel` (count, moving 1) and `kinematics`
(span 1) stepped over each. The worker is not run: a range's walk is the tool stepped from state None at
its first row, which is what `_Walk.step` does. A row is relinked where the window's ids stop mapping one
to one onto the clip's; the id numbers themselves always differ, a walk numbering from its own first row.

The last row, counted from the window's first, at which the two differ, over the 22 windows:

| `merge_ratio` | relinked, windows of 22 | relinked, last | track's signal, median and last | travel's signal, last | kinematics' signal, median and last |
| --- | --- | --- | --- | --- | --- |
| 0, the document's | 0 | none | 5, 23 | 0 | 1, 18 |
| 1.5 | 3 | 59 | 2, 60 | 0 | 0, 59 |
| 3 | 6 | 159 | 9, 161 | 0 | 5, 159 |

At `merge_ratio` 0 the linking never differs: every window's ids are the clip's under a renaming, from the
window's first row to the clip's last. What differs is confined to the window's first rows and has three
causes, each read off the tool. A track alive at the window's first row has fewer hits than the clip's has
and is under `min_rows` for two rows more, which is the signal's difference at rows 0 and 1 in every
window. A track the clip's walk had lost before the window began and takes up again inside it is, to the
window, a new id: the linking agrees under the renaming, since the window never saw the old id, but the
clip's has its hits and the window's waits `min_rows` again, and `kinematics` reads a speed across the gap
where the window's reads NaN. That can happen no later than `lost_rows` after the window's first row, and
the signal follows it by `min_rows` less one: 32 rows here, and 23 is the most seen. `travel` reads 0 at
the window's first row for want of a row before it, and differs at no other.

With `merge_ratio` over 0 there is no such bound. Under a ratio of 3 the six windows that begin
before row 184 all relink last at it, offsets 159 down to 34; under 1.5 the windows at 50, 75 and 100
relink last at row 109 and the one at 25 does not. A track's `area` is the mean over every row it was seen in, the window's mean is over
fewer rows than the clip's, and where a blob's area sits near the ratio of one mean and not the other the
two walks refuse differently. A refusal ends a track, so the difference is a relinking and not a
renaming, and it comes wherever such a blob does, however far into the window. Windows that begin after
row 184 show none on this clip, which says the clip has no later such blob and nothing about a longer one.

So for the Fork: at `merge_ratio` 0 the two agree, under a renaming of ids, past `lost_rows` plus
`min_rows` less one rows from the window's first, and the spec's recommendation stands with that as its
how many. With `merge_ratio` set they do not agree past any row count that can be stated, and a window's
tracks are the clip's only from the same first row.

Three things this bears on that the spec does not say. The renaming is not nothing: csv writes the id,
the draw colours by it and `resolve` reads it, so a row served from the clip's run in place of the
window's changes every id on screen even where the linking is the same. `count` and `size` over tracks
read no id and are the same from any first row, though the node is bound by what it reads; the plan's
`depends_on_row_alone`, which the tree had then and nothing read, was the safe side of that and gave up a
result that is in fact reusable; it was cut the same evening. And `travel`'s one
differing row, with `transitions` by the same construction, is the range's first: either would be free
if stepped with the row before the range's first as its state, which nothing does now.

Not measured: a window through the worker, though the stepping is the same call; a clip with more
contacts, where relinking under `merge_ratio` would be commoner; `lost_rows` other than 30; and the purb
document's hour, whose `merge_ratio` is 0.
