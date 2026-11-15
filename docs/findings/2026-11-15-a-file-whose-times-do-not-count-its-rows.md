# A file whose times do not count its rows: what a seek read, and what telling it costs

2026-11-15, on v5-a-seek-reads-the-row-it-was-asked-for, begun at fcddc126. cv2 5.0.0, its FFmpeg
plugin. Takes up what `2026-11-15-why-no-seek-lands-in-the-mts-first-thirty-rows.md` left unrun: a
file of varying frame rate. `Decoder._row_read` numbers the frame a seek reads by its time against
row 0's, at the container's frame rate; a step numbers a frame by counting. The two are one number
only where every frame is one period after the last.

## Two files with frames gone

Both written from the first 260 frames of `video-tests/00000_168-178.mp4` scaled to 320 wide, with
`-fps_mode passthrough` so the frames kept hold the times they had, libx264, a keyframe every 30:

- `gap.mp4`: frames 40 to 69 gone, `select='not(between(n\,40\,69))'`. The container says 53.739
  rows a second, the stream's 59.94 less the gap.
- `gaps.mp4`: every seventh frame gone, `select='not(eq(mod(n\,7)\,3))'`. The container says 51.434.

By `experiments/2026-11-15-rows-by-a-seek-against-rows-in-order.py`, the first 120 rows, each read
by a seek and compared with the row read in order:

| file | Decoder | rows another than in order | decodes |
| --- | --- | --- | --- |
| `gap.mp4` | fcddc126 | 101 of 120 | 2668 |
| `gaps.mp4` | fcddc126 | 0 of 120 | 271 |
| `gap.mp4` | with the count held | 0 of 120 | 7269 |
| `gaps.mp4` | with the count held | 0 of 120 | 7425 |

On `gap.mp4` at fcddc126 a seek read a row up to 17 from the one asked, before the gap and after
it, and nothing said so beyond the line every inexact container gets. `gaps.mp4` read right by
chance of the arithmetic: frames gone at an even spacing bring the container's rate down by the
share that is gone, so a time at that rate rounds to the count. A file is not shown sound by its
seeks reading right over one stretch.

## What tells such a file

A stepped frame's time. Where a cursor steps, the row is the count, and the frame's time at the
container's rate is either that row or the file's times do not count its rows. By
`experiments/2026-11-15-whether-a-files-times-count-its-rows.py`, rows read in order:

| file | rows | container's rate | a time gave another row |
| --- | --- | --- | --- |
| `00000.MTS` | 600 | 59.940 | no |
| `00000_168-178.mp4` | 590, all | 59.940 | no |
| `rep3_intermittent_crop.MP4` | 600 | 59.940 | no |
| `GX010047c2_02_17_26.MP4` | 600 | 23.976 | no |
| `gap.mp4` | 260, all | 53.739 | yes, at row 5 |
| `gaps.mp4` | 260, all | 51.434 | yes, at row 69 |

The Decoder now compares the two at every step. At the first that differ it says so once on stderr,
empties its cache, numbers no seek on the file from then on, and reaches every row by stepping from
row 0 or from a cursor that has only counted.

## What it costs

By `experiments/2026-11-15-what-timing-every-step-costs.py`, 300 rows in order on one capture, the
read and the `CAP_PROP_POS_MSEC` after it timed apart:

| file | a read, ms | its time, us | share of the read |
| --- | --- | --- | --- |
| `00000.MTS` | 2.813 | 7.12 | 0.253% |
| `00000_168-178.mp4` | 2.686 | 6.56 | 0.244% |

Row 0's time, read on a capture of its own, is now read at a Decoder's first step and not its first
seek; the earlier finding has what that capture costs. On a file found out, a read behind the
cursor is a walk from row 0: the decodes above went from 2668 to 7269 over the same 120 reads.

## What it does not tell

- A seek that lands past a gap no step of this Decoder has crossed is numbered by its time, as
  before, until a step crosses one. A walk from the top crosses every gap; a scrub into the far end
  of a file not yet walked does not.
- A file whose frames gone are spaced so evenly that every time rounds to its count is never found
  out, and its seeks read right for the same reason.
- What a node computed from a row a seek misnumbered, before the file was found out, stays in the
  memo under that row. The Decoder empties its own cache and reaches no other store.

Not run: a file whose container claims no frame rate, which the Decoder takes as 30; a file of
varying rate from a phone or a screen recorder, where the times are the device's and not ffmpeg's
`select`; the player on screen over either gap file.
