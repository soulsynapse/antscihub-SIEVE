# A file whose times do not count its rows: what a seek read, and numbering a seek by the packets' times

2026-11-15, on v5-a-seek-reads-the-row-it-was-asked-for, begun at fcddc126. cv2 5.0.0, its FFmpeg
plugin. Takes up what `2026-11-15-why-no-seek-lands-in-the-mts-first-thirty-rows.md` left unrun: a
file of varying frame rate. At fcddc126 `Decoder._row_read` numbered the frame a seek reads by its
time against row 0's, at the container's frame rate; a step numbers a frame by counting. The two are
one number only where every frame is one period after the last.

## Two files with frames gone

Both written from the first 260 frames of `video-tests/00000_168-178.mp4` scaled to 320 wide, with
`-fps_mode passthrough` so the frames kept hold the times they had, libx264, a keyframe every 30:

- `gap.mp4`: frames 40 to 69 gone, `select='not(between(n\,40\,69))'`. The container says 53.739
  rows a second, the stream's 59.94 less the gap.
- `gaps.mp4`: every seventh frame gone, `select='not(eq(mod(n\,7)\,3))'`. The container says 51.434.

By `experiments/2026-11-15-rows-by-a-seek-against-rows-in-order.py`, the first 120 rows, each read
by a seek and compared with the row read in order, under three Decoders: fcddc126's; c4788dcf's,
which compared a stepped frame's time at the container's rate with the count and, at the first that
differed, numbered no seek and stepped to every row from row 0; and the one this finding ends at,
which numbers a seek by the packets' times.

| file | Decoder | rows another than in order | decodes |
| --- | --- | --- | --- |
| `gap.mp4` | fcddc126 | 101 of 120 | 2668 |
| `gaps.mp4` | fcddc126 | 0 of 120 | 271 |
| `gap.mp4` | c4788dcf, the count held | 0 of 120 | 7269 |
| `gaps.mp4` | c4788dcf, the count held | 0 of 120 | 7425 |
| `gap.mp4` | by the packets' times | 0 of 120 | 951 |
| `gaps.mp4` | by the packets' times | 0 of 120 | 241 |
| `00000.MTS` | by the packets' times | 0 of 120 | 686 |
| `00000_168-178.mp4` | by the packets' times | 0 of 120 | 241 |

On `gap.mp4` at fcddc126 a seek read a row up to 17 from the one asked, before the gap and after
it, and nothing said so beyond the line every inexact container gets. `gaps.mp4` read right by
chance of the arithmetic: frames gone at an even spacing bring the container's rate down by the
share that is gone, so a time at that rate rounds to the count. A file is not shown sound by its
seeks reading right over one stretch. The `.MTS`'s and the crossings clip's decodes are what they
were at fcddc126.

## The packets' times are the frames'

A capture opened with `CAP_PROP_FORMAT` -1 hands out the stream's packets with no frame decoded, and
`CAP_PROP_POS_MSEC` after each grab is that packet's time. By
`experiments/2026-11-15-a-files-packet-times-against-its-frames.py`, every packet's time, sorted,
against the same property after each of the first 300 frames read in order on a capture that decodes:

| file | MB | packets | read in, s | distinct times | smallest step, ms | largest | rows of 300 with another time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `00000.MTS` | 2026 | 38100 | 1.86 | 38100 | 16.678 | 16.689 | 0 |
| `GX010047c2_02_17_26.MP4` | 3382 | 11328 | 2.38 | 11328 | 41.708 | 41.708 | 0 |
| `rep3_intermittent_crop.MP4` | 68 | 30579 | 0.07 | 30579 | 16.683 | 16.683 | 0 |
| `00000_168-178.mp4` | 27 | 590 | 0.04 | 590 | 16.683 | 16.683 | 0 |
| `gap.mp4` | 0 | 260 | 0.01 | 260 | 16.683 | 517.183 | 0 |
| `gaps.mp4` | 0 | 260 | 0.01 | 260 | 16.683 | 33.367 | 0 |

So the sorted times are a table of the file's rows: the time at r is row r's, whatever the spacing,
and a frame's row is its time's place in the table. Every file's first time is 0, so row 0's time
needs no capture of its own. The seconds are with each file already in the system's cache; the
GoPro file's container claims 11328 rows and its stream ends at 11308, so the table may be longer
than the rows a read hands out, which changes no row before the end.

`CAP_PROP_PTS` is not that time: on `gap.mp4` it gave 233 distinct values for 260 packets, two
frames sharing one where the container's rate rounds them together.

## What the Decoder does with it

`decoder.frame_times` reads the table and keeps it in the store, `frame-times/<footage print>.npy`,
so a file's packets are read once and a later launch loads the table. The window begins the reading
on a thread of its own as a video opens; a seek that comes before it is done waits on it and begins
no second. A Decoder takes the table at its first seek. The frame a seek reads is numbered by its time's place in it. With the table held, a stepped frame's time is
compared with the time at its count; one that differs, or a landing whose time is no packet's, or a
file the plugin hands out no packets of, ends the numbering of seeks on that file: it is said once
on stderr, the cache is emptied, and every row is stepped to from row 0, as c4788dcf did for any
file found out.

By `experiments/2026-11-15-whether-a-files-times-count-its-rows.py`, one row far on and then 600
rows in order, or all the file has: on the `.MTS`, the crossings clip,
`rep3_intermittent_crop.MP4`, the GoPro file and both gap files every stepped frame's time was its
row's packet's, and seeks stayed numbered.

## What it costs

The table's read above, once a file: about a second a gigabyte here with the file cached. The
packets themselves are read, so from a disk that has not the file cached it is the disk's time for
the file. By `experiments/2026-11-15-what-a-kept-table-of-frame-times-costs.py`, the reading and
then the kept table with the process's own copy dropped:

| file | off the packets, s | from the kept table, ms | the table, bytes |
| --- | --- | --- | --- |
| `00000.MTS` | 1.24 | 0.7 | 304928 |
| `GX010047c2_02_17_26.MP4` | 2.34 | 0.6 | 90752 |

The kept table's figure has the footage print already taken in the process; a launch takes it anew,
two megabytes of the file read and digested. What a user waits is a first seek made before the
reading begun at the open is done, on a file no table is kept of; the wait is on the worker's
thread, under the lock a read holds, and the window draws meanwhile.

By `experiments/2026-11-15-what-timing-every-step-costs.py`, 300 rows in order on one capture, the
read and the `CAP_PROP_POS_MSEC` after it timed apart:

| file | a read, ms | its time, us | share of the read |
| --- | --- | --- | --- |
| `00000.MTS` | 2.813 | 7.12 | 0.253% |
| `00000_168-178.mp4` | 2.686 | 6.56 | 0.244% |

The place in the table, a binary search, is not in that figure.

## What it does not tell

- A file with two packets a frame, field-coded interlaced video, has a table twice its rows: the
  first stepped frame past row 0 has another time than its count's, and the file falls to stepping
  from row 0. None was tried.
- What a node computed from a row a seek misnumbered, before a file was found out, stays in the
  memo under that row. The Decoder empties its own cache and reaches no other store.
- A table is kept under the footage print, which reads a file's size and its first and last
  megabyte: of two files as long that differ only between those, the second takes the first's
  table, and at the first of its frames whose time differs from it reads its own off its packets
  and keeps that over the first's, as the first then does at its next launch.
- A kept table outlives its file and nothing removes it; the store's control counts its bytes with
  the rest.
- A bare walk's process and a tool run alone set no store and keep no table.

Not run: a file of varying rate from a phone or a screen recorder, where the times are the device's
and not ffmpeg's `select`; a file from a cold disk; the reading begun at an open against a walk
begun beside it, both reading one disk; a file the plugin hands out no packets of; the
player on screen over either gap file.
