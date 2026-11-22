# A bare walk of the whole camera file dies of an access violation

2026-11-21, on `v5-playground-one-store` and on `v5` at `b23ff2c4`. Python 3.13.5, numpy 2.5.4,
cv2 5.0.0, Windows 11.

## What was run

`docs/findings/experiments/bare_walk_thrice.py video-tests/purb-168-178.json video-tests/00000.MTS <folder>`:
the crossings clip's document (gray, threshold, detect, then track, size, count, travel) walked
bare over all 38100 rows of the file it was cut from, each walk its own process.

## What happened

| tree | results kept between walks | died at | exit | where the fault handler put it |
|---|---|---|---|---|
| playground | yes, first walk | about 51 s | 0xC0000005 | not taken |
| playground | yes, second walk | about 45 s | 0xC0000005 | not taken |
| playground | yes, third walk | about 10 s | 0xC000001D | not taken |
| playground | no (the folder unmakeable) | row 22607 | 0xC0000005 | `tools/track.py:80`, `pairs.sort(reverse=True)` in `_link_row` |
| `v5` | there is none | row 13855 | 0xC0000005 | the same line |

No walk of the five ended. The rate until each died was about 255 rows a second. The same document
over the ten-second clip (`video-tests/00000_168-178.mp4`) ends every time, six walks of six.

## What it shows and does not

- The fault is not this branch's: `v5` dies the same way with no keeper in it.
- It is not at one row: 13855 and 22607 under the same document and file. A fault that moves is
  not `track`'s arithmetic on one bad table; it reads as memory already spoiled by the time a
  sort walks it, or as memory run out. Which was not found. Nothing was measured of the
  process's memory, and no walk was made without `track`, without the decoder's reading ahead,
  or under another cv2.
- The line named is where the fault surfaced twice of two, which is thin for calling it the cause.
- The third playground walk read its detect rows from the folder the two dead walks had filled
  and went about five times as fast until it too died, with a different exit code.

## What would settle it

The same walk with `track` taken out of the document; with the process's memory printed beside
the rows done; and under the cv2 the player was last known to walk this file whole with, if it
ever did.
