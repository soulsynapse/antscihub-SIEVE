# Why no seek lands in the `.MTS`'s first thirty rows, and what gives the row read

2026-11-15, on v5-a-seek-reads-the-row-it-was-asked-for, begun at 729bbead. cv2 5.0.0, its FFmpeg
plugin on avformat 61.7.100. Takes up the two things
`2026-11-15-a-cut-clips-rows-against-the-plates.md` did not look into: why no seek on
`video-tests/00000.MTS` lands before row 30, and whether the frame's time gives the row on the MP4s.

## The cause

`ffprobe` of the `.MTS`'s video stream: H.264 with one frame of reordering, `time_base` 1/90000,
`start_pts` 91502. Its first packets, in file order:

| packet | pts | dts | keyframe |
| --- | --- | --- | --- |
| 0 | 91502 | 90000 | yes |
| 1 | 93003 | 91501 | |
| 2 | 94505 | 93003 | |
| 30 | 136547 | 135045 | yes |
| 60 | 181592 | 180090 | yes |

The stream's start is the first packet's pts, and every dts runs one frame ahead of its pts. A seek
to row 0 asks for the stream's start, 91502. A transport stream has no index and is searched by dts,
and the last packet whose dts is not past 91502 is packet 1, at 91501: one past the keyframe. A
decoder begun there has no picture to hand out until the next keyframe, packet 30. So the earliest
time the plugin can ask for already lies behind the first keyframe, and rows 0 to 29 are reached
only by reading from the file's top. The search by dts and the unchecked landings below are as I
remember `cap_ffmpeg_impl.hpp` and FFmpeg's `mpegts.c`, not read from this build's source; the
packets and the landings are measured.

What the plugin says of a landing, by the table of the earlier finding and the one here: of a seek
to row 0 it says 0 and of one to row 1 it says 1, with no look at what it got; of one to rows 2 to
30 it says 30, having read row 30 away, so the next read is 31. Only a target it could get behind is
said rightly. An MP4 is sought through its index, by keyframe, and row 0's keyframe is found.

## The frame's time

`docs/findings/experiments/2026-11-15-the-row-a-frames-time-gives.py`: the first rows in order, the
row `CAP_PROP_POS_MSEC` gives after each read against the count; then 27 seeks, each on a fresh
capture, to rows 0 to 61 and a spread up to the last row held.

| file | rows in order | their time gives another row | row 0's time | seeks where what was said is not the row read | seeks where the time is not |
| --- | --- | --- | --- | --- | --- |
| `00000.MTS` | 400 | 0 | 0 | 8 of 27, every target from 0 to 30 | 0 |
| `00000_168-178.mp4` | 400 | 0 | 0 | 0 of 27 | 0 |
| `rep3_intermittent_crop.MP4` | 400 | 0 | 0 | 0 of 27 | 0 |
| `GX010047c2_02_17_26.MP4` | 90 | 0 | 0 | 0 of 27 | 0 |

No time lay further than 0.0003 of a row from a whole one. On the `.MTS`, 40 seeks to rows drawn at
random from 31 to the container's 38100 less 600, on one capture: at each, what was said, the
target and the row by the time were one; the rows read there were not compared with rows in order.

## After the change

`Decoder._seek` reads a frame after each seek and numbers it by its time against row 0's, asks
further back where that is past the target, and with a seek to row 0 still past it reopens the
cursor and steps, holding the row that seek read so a later target before it is not sought at all.
`docs/findings/experiments/2026-11-15-rows-by-a-seek-against-rows-in-order.py`, the first 120 rows
from the last to the first on a Decoder holding one frame:

| file | rows by a seek that are another row than in order | seeks | decodes |
| --- | --- | --- | --- |
| `00000.MTS` | 0 of 120, where the earlier finding had 19 | 121 | 686 |
| `00000_168-178.mp4` | 0 of 120 | 121 | 241 |
| `rep3_intermittent_crop.MP4` | 0 of 120 | 121 | 241 |

The `.MTS`'s 445 decodes over two a seek are its first thirty rows, each read from the top. The two
MP4s were run before the earliest landing was held, which they never set.

## What it costs

`docs/findings/experiments/2026-11-15-what-numbering-a-seek-by-its-time-costs.py` against the
Decoder of 729bbead, each workload on a fresh Decoder holding one frame, the two turn about, the
median of three in ms and the three's range beside it:

| workload | `.MTS` before | `.MTS` after | clip before | clip after |
| --- | --- | --- | --- | --- |
| an opening and its first seek, to the middle row | 203 (199-211) | 256 (252-258) | 108 (108-117) | 167 (162-168) |
| a seek to a row at random, of 20 | 80 (73-84) | 86 (84-86) | 137 (122-138) | 144 (137-148) |
| a seek one row back, of 20 | 63.9 (63-65) | 62.5 (62-63) | 80.1 (80-84) | 80.8 (79-84) |
| a row in order, of 200 | 2.71 (2.6-2.9) | 2.79 (2.6-3.6) | 3.42 (3.4-3.5) | 3.47 (3.4-3.7) |
| a seek one row back from row 29 to 0 | 137 (135-175), the wrong rows | 91 (90-112) | 37.7 (37.6-38.0) | 36.9 (36.6-37.1) |

One cost is outside the repeats' spread: a Decoder's first seek, 53 ms dearer on the `.MTS` and
58 ms on the clip, which is `_first_ms` opening a capture of its own and reading row 0. It is paid
once a Decoder and is the whole of what the 20 seeks at random show, some 3 ms each when shared out.
A seek after it, a seek one row back and a row in order are inside the spread. The `.MTS`'s first
thirty rows are cheaper than they were, being read from the top with no seek once the earliest
landing is held.

Not run: the GoPro file through the Decoder's seeks, or its cost; any file whose row 0's time is
not 0, which `_first_ms` is there for; a file of varying frame rate, where the time's row and the
count part and the plugin's own checked landings are by time as well; the end of any stream; the
player on screen; the simulations. Not tried: taking row 0's time from the first cursor that reads
row 0 in place of a capture of its own, which would spare the first seek's cost where a walk from
the top came first.
