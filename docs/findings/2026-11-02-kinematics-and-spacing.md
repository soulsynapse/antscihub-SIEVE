# Kinematics and spacing on the purb document: per-row heading is sub-pixel noise, a ten-row step resolves the body axis only off contacts, and the contact rate needs the pile filtered out

2026-11-02, on v5-blob-detection over 1697cfff with the working tree that added tools/kinematics.py
and tools/spacing.py, by docs/findings/experiments/2026-11-02-kinematics-and-spacing.py on
video-tests/purb-settings.json, rows 2000 to 2599 of video-tests/00000.MTS, the rows and settings
of docs/findings/2026-11-01-track-diagnostics.md, luma at 0.5 (960×540). Loose means outside the
cluster box that finding drew, (330, 160) to (520, 300); the records inside it are the split's
pieces of the pile. The heading-versus-angle figures past the first table are from a sweep run by
hand over the same rows, not from the script.

## Kinematics

kinematics over the 600 rows' tracks costs 65 ms. The loose records with a step, 5054 of them:

| | |
|---|---|
| speed, px per row | p5 0.04, p50 0.30, p95 1.39, p99 2.53, max 3.80 |
| over 0.5 px per row | 28.9% |

No step reaches track's max_step of 4, which is what the diagnostics finding read from the linker's
side. At 59.94 rows a second the median step is a third of a pixel, so a per-row heading is the
centroid's jitter and not the ant's direction: of the records over 0.5 px per row, 37% have a
heading within 20 degrees of the moment ellipse's axis, mod 180.

Heading from a step spanning more rows, against the axis at the step's end, for loose ids with
area under 1000 px, moving at least 3 px and 0.3 px per row over the span:

| span, rows | moving steps | heading within 20 degrees of the axis |
|---|---|---|
| 1 | 15 | 33% |
| 5 | 286 | 30% |
| 10 | 585 | 54% |
| 20 | 456 | 57% |
| 30 | 376 | 58% |

At ten rows, by how far the ant went: 3 to 5 px, 70% within 20 degrees; 5 to 20 px, 30 to 39%;
over 20 px, 88% of eight. Blobs' angle and the heading share a convention (a bar drawn down and
right reads 45 in both). A picture of the worst cases at ten rows shows what the middle band is:
an ant in contact with another, whose centroid moves with the merged pixels and not along its
body, and an ant turning, whose axis at the step's end is not the step's direction; the straight
walkers agree within a few degrees. So motion resolves the axis's 180 degrees only for a free ant
walking straight over a span of rows, and the tool as built has no span: a column resolving
`angle` by `heading` would be wrong on most rows of this clip at one row, and a `span` knob, or a
smooth over the track before the heading is taken, is the call this leaves open.

## Spacing

| method, over the 600 rows | all blobs, px | loose only, px |
|---|---|---|
| min nearest-other distance | p5 15.4, p50 21.4, p95 29.3 | p5 15.4, p50 36.5, p95 95.5 |
| mean nearest-other distance | p5 42.1, p50 51.4, p95 61.5 | p5 67.9, p50 87.1, p95 119.6 |

| pairs within r, a row | all blobs, mean and rows with any | loose only |
|---|---|---|
| 10 px | 0, 0% | 0, 0% |
| 20 px | 0.25, 24% | 0.21, 20% |
| 40 px | 5.50, 100% | 1.05, 63% |

An ant is about 40 px long at this scale (area p50 185 at aspect 4.9), so pairs within 20 px are
centroids under half a body apart, a contact, and 40 px is a body. Over all blobs the 5.5 pairs a
row within 40 px and the 21 px median nearest distance are the pile's fragments against each
other, so spacing fed the whole table reads the split, not the colony; the contact rate is the
loose column, 0.21 pairs a row within 20 px, and it needs the pile out of the table first, by
filter on cx and cy, by a membership column from sample on the pile's mask, or by max_area with
split off. Each method is 12 to 15 ms over the 600 rows.

## What this says

Both tools cost nothing and read what they say. Kinematics' speed is the number the moving
threshold in travel and the displacement in tracks-filter were approximating; its heading is
only a direction over a span this clip's frame rate makes several rows long, and the span is not
in the tool. Spacing is the contact rate once the pile is a region and not blobs, which
docs/spec/blob-tools.md already argued for on other grounds.
