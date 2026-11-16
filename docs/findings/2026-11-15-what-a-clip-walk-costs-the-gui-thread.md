# What a clip walk costs the GUI thread

2026-11-15. A clip walk of the thermal hysteresis file, 345595 rows of 1920x1080 at 60 fps, a
served region of 256x258 walked through threshold, detect, track, size, count, travel, smooth and
csv, on the player at e22531a0 with the monitor open. The walk began at 1581 rows a second and was
at 738 five minutes on, its unprobed ms a row rising with it. The figures are from the monitor's
history of that run, `sieve-history-20261115-182655.json`, cut into 40 s; the history is in no
repo. Experiment for the strip:
`docs/findings/experiments/2026-11-15-what-a-strip-paint-costs-as-a-clip-walk-grows.py`.

## The stores did not slow it

The memo was at its 4.0 GB before the clip walk began and the region's cache at its 4.0 GB within
20 s of it. The walk's fastest 20 s, 1798 rows a second at 0.55 ms a row, were with both full, and
every store said 0 run again throughout.

## The GUI thread did

| s into the history | rows a second | unprobed, ms a row | paint monitor, ms a second | slot monitor, ms a second | paint strip, ms a second | paint strip, ms a call | slot monitor, ms a call |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 280 | 1581 | 0.12 | 77 | 75 | 15 | 1.7 | 18.8 |
| 360 | 1003 | 0.24 | 174 | 100 | 85 | 10.1 | 25.1 |
| 440 | 806 | 0.37 | 178 | 206 | 120 | 14.9 | 51.6 |
| 560 | 738 | 0.52 | 192 | 194 | 188 | 23.7 | 48.7 |

The clip walk's 1260 buckets of 0.25 s, by the share of each the GUI thread spent in its own spans:

| GUI thread busy | buckets | wall, ms a row, median | unprobed, ms a row, median |
| --- | --- | --- | --- |
| under 20% | 110 | 0.62 | 0.12 |
| 20 to 40% | 464 | 0.96 | 0.23 |
| 40 to 60% | 555 | 1.16 | 0.33 |
| 60 to 80% | 119 | 1.67 | 0.61 |
| over 80% | 12 | 2.26 | 0.90 |

The share against the unprobed ms a row correlates at 0.58, against the wall ms a row at 0.44. What
of a row no span covers is the worker's own Python between its tools' calls, which waits on the
interpreter the GUI thread holds.

Two of the GUI thread's spans grow with the walk. The monitor's slot and paint, about 390 ms of
every second by the end, are the monitor's own and go when it is closed. The strip's paint is the
player's.

## The strip

Each `clipReady`, about 8 a second, handed the strip the clip's signal so far, and the strip drew
all of it anew: the min and max of every pixel column as one antialiased polygon, which was half
the paint, and a Python call a column around it. Offscreen, the signal noise, the strip 1800 px:

| rows walked | 20k | 80k | 160k | 240k | 330k |
| --- | --- | --- | --- | --- | --- |
| ms a paint before, at a scale of 1.0 | 0.5 | 1.6 | 4.4 | 10.2 | 13.0 |
| ms a paint before, at a scale of 1.5 | 0.5 | 3.8 | 13.9 | 24.6 | 41.1 |
| ms a paint now, after 120 more rows, at 1.0 | 0.39 | 0.42 | 0.49 | 0.54 | 0.61 |
| ms a paint now, of a strip that has drawn nothing, at 1.0 | 0.6 | 1.2 | 3.0 | 7.9 | 9.5 |

The strip now holds the series on a pixmap of their own, with what it drew there as each stretch's
columns, their min, max and gate. A paint asked for after the series change reduces the rows to
columns again, which is the 0.4 to 0.6 ms, finds the columns that are other than those drawn, and
draws those alone. A window, a hover and a playhead that move draw no series.

Qt antialiases a line's end differently from the same point drawn on as a join, two columns back
from it: 70 levels of 255 on a clip with columns between its rows. So three columns before the
first altered one are drawn anew, with four more either side handed to the painter. With that, 168
paints of strips grown in steps were each the paint of a strip drawn whole, pixel for pixel, over
clips of many rows a column, a row a column and columns between the rows.

Against the strip before, a whole paint differs by one level of 255 on some hundred pixels of
54000 and by no more anywhere, over 30 paints: the series reach the widget through a transparent
pixmap where they were drawn on the field.

## Not measured

The player on screen with the strip as it now is, so the walk's rate with it; the paint now at a
scale of 1.5; a signal that is not noise, which the polygon was cheaper on; what in the monitor's
slot grows.
