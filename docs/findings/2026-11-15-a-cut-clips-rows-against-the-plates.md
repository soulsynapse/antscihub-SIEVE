# A cut clip's rows against the plate's

2026-11-15, on v5-region-serves-cut-files-from-the-store at 36e3565e. Experiment:
`docs/findings/experiments/2026-11-15-a-cut-clips-rows-against-the-plates.py`, run once a file. The
walk, the timeline and the held results take a served clip's row r for the plate's row r, and
`Graph._compute` takes the clip's end for the plate's; nothing in the tree compared the two.

One shape of each file's geometry is cut by `tools/_cutfile.py`'s `command` at each quality, outside
the store, and both files are read by `sieve_player.decoder.Decoder`. In order: every row of the
clip against the plate's row of that number cut to the rect. By a seek: 25 or 26 rows, the first
three, the last three and 20 drawn at random, each on fresh decoders, the clip's row against the
plate's rows two either side. Then each of the plate's first 120 rows, and the lossless clip's, by a
seek on a fresh decoder against the same file's read in order.

| file | rows cut | lossless, rows in order not equal to the plate's | standard, mean abs difference at worst | counts at the end, clip and plate | lossless rows by a seek nearest another plate row |
| --- | --- | --- | --- | --- | --- |
| `00000_168-178.mp4`, 1920x1080 H.264 in MP4 | all 590 | 0 | 1.707 | 590, 590 | 0 of 26 |
| `GX010047c2_02_17_26.MP4`, 5312x2988 | the first 60 | 0 | 1.101 | unread | 0 of 25 |
| `00000.MTS`, H.264 in a transport stream | the first 120 | 0 | 1.446 | unread | 2 of 25 |

Read in order, a lossless clip is the plate's rows cut, equal in every value, on all three files: no
row is dropped, repeated or moved, and the even rect keeps the chroma. A clip at standard differs at
every row by under two levels in the mean, and by a seek each of its rows is nearest its own plate
row on the two MP4s.

The two rows that disagree on the `.MTS` are the plate decoder's and not the cut's. Of the plate's
first 120 rows read by a seek on a fresh decoder, 19 are another row than the same file read in
order: rows 13 to 30 each hand out the row 30 after it, and row 31 hands out row 32. Of the lossless
clip's 120, none. Of `00000_168-178.mp4`'s own first 120, none. So on the transport stream a scrub,
or a walk that begins by a seek, reads other rows than a walk from row 0 does, and a node served a
clip of it reads the right ones. `Decoder._seek` reads its landing back from the plugin and steps
from there; here what the plugin says it landed on is not where it is.

`docs/findings/experiments/2026-11-15-where-a-seek-on-the-mts-lands.py` reads that landing. The
file's keyframes are at rows 0, 30 and 60, and no seek lands in the first thirty rows:

| target | `CAP_PROP_POS_FRAMES` before the read | the row read | the row by `CAP_PROP_POS_MSEC` after it |
| --- | --- | --- | --- |
| 0, after a seek to 40 | 0 | 30 | 30 |
| 1 | 1 | 31 | 31 |
| 12 | 30 | 31 | 31 |
| 30 | 30 | 31 | 31 |
| 31 | 31 | 31 | 31 |
| 40, 61, 90 | the target | the target | the target |

A row from 13 to 30 is sought one short, is said to have landed past it, and is sought again from
row 0, which is said to be row 0 and is row 30; row 31 is sought at 30, said to be there, and is 31.
The frame's time after the read gives the row read in every case.

Not run: the per-file seek check on the GoPro file, which did not end inside a minute; the end of
the GoPro file and of the `.MTS`, where the container's claim and the stream part; any row of the
`.MTS` past 120; a clip of a clip; a seek on the `.MTS` past row 150. Not looked into: why no seek
lands in the first thirty rows, and whether the frame's time gives the row on the two MP4s.
