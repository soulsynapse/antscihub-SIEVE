# libav asked directly against the plugin: what a seek lands on, and what a row takes

2026-11-15, on v5-a-seek-reads-the-row-it-was-asked-for, at 25b5c3da. cv2 5.0.0, whose FFmpeg plugin
is built on avcodec 61.19.100; PyAV 19.0.2, on avcodec 63.1.102, installed outside the player's
environment for the runs and no requirement of it. The question: the Decoder's seeks are numbered
through `cv2.VideoCapture`, which says nothing of a frame but a time in ms and misreports where a
seek landed; whether asking libav itself, where a frame carries its pts, takes the inexact seek
away, and what it costs or saves. Nothing of the player was changed for it.

## A seek

By `experiments/2026-11-15-rows-by-a-seek-through-libav-against-the-decoders.py`: the first rows of
each file in order through libav, then each from the last to the first by a seek to its pts,
`backward=True`, frames decoded until that pts comes; a seek whose first frame out is past the row
is asked again further back, twice as far each time, as `Decoder._seek` asks. Beside it the same
rows on a Decoder holding one frame. 120 rows, the GoPro file 40.

| file | rows | libav's seeks | landed past the row | another row than in order | libav, ms a row | the Decoder, ms a row |
| --- | --- | --- | --- | --- | --- | --- |
| `gap.mp4` | 120 | 120 | 0 | 0 | 1.6 | 1.7 |
| `gaps.mp4` | 120 | 120 | 0 | 0 | 1.8 | 2.1 |
| `rep3_intermittent_crop.MP4` | 120 | 120 | 0 | 0 | 6.0 | 4.9 |
| `00000_168-178.mp4` | 120 | 120 | 0 | 0 | 59.8 | 59.2 |
| `00000.MTS` | 101, the budget spent | 614 | 513 | 0 | 220.2 | 93.2 |
| `GX010047c2_02_17_26.MP4` | 40 | 40 | 0 | 0 | 327.8 | 440.5 |

Every row through libav, in order and by a seek, has the luma plane the Decoder hands out for that
row, on all six files.

On the transport stream five seeks of six through libav land past the row asked. A probe not kept
asked single rows: a seek to row 119's pts hands out row 120 first, to row 100's row 120, to row
61's row 90, to row 45's row 60; asked one frame's time earlier, row 61 hands out row 60 and row 0
row 0, and rows 119, 100 and 45 are as before. The keyframes are at every thirtieth row. So what
`2026-11-15-why-no-seek-lands-in-the-mts-first-thirty-rows.md` found is libav's searching of a
transport stream and not the plugin's own: a Decoder on libav keeps the asking further back, and
the plugin's own asking, inside its seek, is the cheaper of the two here. On the four MP4s whose
packets begin at their first frame no seek through libav landed past, which is what the Decoder
finds of them through the plugin.

`gap.mp4` and `gaps.mp4` are written as that finding's sibling,
`2026-11-15-a-file-whose-times-do-not-count-its-rows.md`, says, anew for these runs.

## The GoPro file's first twenty packets

The first frame libav hands out of `GX010047c2_02_17_26.MP4` is the packet 20th from the first by
its pts: the packets' pts begin at -20020 in the stream's 1/24000, a keyframe, and the frame at pts
0 is the 21st. The twenty before it are decoded and not handed out. The plugin hands out the same
frame first, its plane being libav's, and by a probe not kept says a time of 0.0 both of that frame
and of the first packet, 41.708 ms apart thereafter in both. So `decoder.frame_times` has twenty
times more than the file has frames, and row r's frame has the time at r only because the packets
are evenly spaced: the table and the frames are counted from two different zeros. That is read off
what the plugin answers and not off its source. A file with such a head and uneven spacing would
have its stepped frames' times differ from the table and fall to stepping from row 0; none was
tried. By that the stream would end twenty rows short of the container's claim; no read was taken
that far.

## The packets' times

| file | packets | through libav, s | through the plugin, s |
| --- | --- | --- | --- |
| `00000.MTS` | 38100 | 1.21 | 1.14 |
| `GX010047c2_02_17_26.MP4` | 11328 | 0.77 | 2.06 |
| `rep3_intermittent_crop.MP4` | 30579 | 0.07 | 0.06 |
| `00000_168-178.mp4` | 590 | 0.04 | 0.04 |

libav's packet also says whether it is a keyframe and its dts, which the plugin's does not.

## A row in order

By `experiments/2026-11-15-what-a-row-in-order-takes-through-libav-against-the-plugin.py`: each way
from a fresh open, 300 rows after 30 not timed, the GoPro file 150; ms a row. Where two figures
stand, a second run, the GoPro's over 60 rows.

| way | `00000.MTS` | `00000_168-178.mp4` | `GX010047c2_02_17_26.MP4` | `rep3_intermittent_crop.MP4` |
| --- | --- | --- | --- | --- |
| the plugin's BGR | 2.59, 2.51 | 2.41, 2.52 | 18.83, 17.58 | 0.11 |
| the plugin's plane, unconverted | 1.27, 1.29 | 1.11, 1.00 | 9.79, 9.14 | 0.07 |
| libav, the frame decoded and not taken | 0.83, 0.83 | 0.68, 0.67 | 7.93, 7.50 | 0.04 |
| libav's luma plane copied out | 1.00, 0.97 | 0.75, 0.80 | 8.25, 8.15 | 0.05 |
| libav's frame converted to BGR | 1.16, 1.13 | 0.91, 0.91 | 8.94, 8.97 | 0.06 |
| the Decoder's bgr | 2.99, 3.03 | 2.47, 2.86 | 20.95, 22.07 | 0.19 |
| the Decoder's luma | 1.35, 1.51 | 1.08, 1.23 | 9.96, 9.60 | 0.11 |

BGR through libav takes 0.36 to 0.51 of the plugin's on the three camera files, and the luma plane
0.68 to 0.89 of the plugin's unconverted plane.

The last row each way handed out was compared with the plugin's. libav's luma plane is the plugin's
on every file. libav's BGR is the plugin's on the .MTS and the crossings clip, both `yuv420p` and
limited range, and is other values on the GoPro file, `yuvj420p`, full range, BT.709: on its first
frame, by a probe not kept, 87% of the values differ, by 1.5 in the mean and 18 at most, whichever
interpolation libav is asked for. The two convert that file by different rules and which is the
file's own was not settled.

## What it does not tell

- Where the time goes. The two are different builds of FFmpeg, two major versions apart, with
  whatever threads each sets; the decode alone is faster through libav, the conversion to BGR more
  so, and neither was taken apart into build, threads and the plugin's own copying.
- What a Decoder on libav would take. The figures are bare loops; the Decoder's cache, its lock and
  its two cursors are in neither libav row.
- Anything of a walk in the player, where the tools' time stands beside the decode's.
- A file from a cold disk, a phone's or a screen recorder's file, field-coded interlaced video, a
  stream that is not H.264.
- Whether PyAV's wheel, which carries its own FFmpeg, loads beside cv2's in the player's process
  as it did in these scripts: it did here, for the length of each run.
