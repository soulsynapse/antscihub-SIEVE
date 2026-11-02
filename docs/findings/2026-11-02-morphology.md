# Morphology between threshold and blobs on the purb document: opening cuts an ant at its waist, closing mends nothing the tracks lack

2026-11-02, on v5-blob-detection over a2a6afc9 with the working tree that added tools/morphology.py,
by docs/findings/experiments/2026-11-02-morphology.py on video-tests/purb-settings.json, rows 2000 to
2599 of video-tests/00000.MTS, the same ten seconds as docs/findings/2026-11-01-track-diagnostics.md,
luma at 0.5 (960×540), threshold 72 inverted, blobs 90 to 6731 px with split on and core 65, track at
its defaults. Loose means a record or an id outside the cluster box that finding drew, (330, 160) to
(520, 300). A gap is rows an id went unseen between two takes, the diagnostics finding's
reacquisition, which it read as an ant dipping under the threshold.

docs/spec/blob-tools.md listed morphology as the fix for detection flickering at the area cut, which
docs/findings/2026-11-01-ants-blob-features-and-linking.md measured at threshold 79 and min_area 230,
where p5 of the ants' area sat on the cut. The purb document has since moved both: at 72 and 90 the
loose records' area is p5 147, p50 185, and 0.3% of them lie within a tenth above the cut. On these
settings there is no area flicker for an opening to steady.

## Variants, same rows

| mask | op cost ms/row | mask regions/row under 90 px | loose records/row, area p5 / p50 | loose ids ≥ 3 rows | rows seen per loose id p50 | loose gaps / rows lost |
|---|---|---|---|---|---|---|
| threshold alone | 0 | 120.9 | 8.6, 147 / 185 | 18 | 226 | 165 / 603 |
| open, radius 1 | 0.21 | 32.5 | 10.4, 91 / 134 | 71 | 47 | 2184 / 8525 |
| open, radius 1, 2 iterations; open, radius 2 | 0.24 | 52.8 | 10.2, 93 / 133 | 73 | 60 | 3043 / 11502 |
| close, radius 1 | 0.26 | 45.7 | 7.6, 161 / 227 | 20 | 85 | 183 / 636 |
| close, radius 2 | 0.29 | 23.5 | 7.0, 183 / 260 | 21 | 98 | 323 / 756 |

The two openings of radius 1 twice and radius 2 give identical counts, since a square kernel iterated
is the larger square kernel.

## Opening

Over 60 rows spaced across the window, for each loose ant's own pixels, the regions of the opened
mask lying on them: 25% of ants leave no region of 90 px or more, 58% leave one, 17% leave two or
more, with two specks under 90 px per ant on average; the largest piece is p50 100 px against a cut
of 90, p5 74. The ants' minor axis is p50 8.5 px at this scale and the neck and petiole are one or
two pixels, so a radius-1 square erosion severs head, thorax and gaster (the experiment's picture of
row 2300 shows it on six ants) and what survives sits on the area cut, which is where the 25.7% of
loose records within a tenth of min_area and the fourfold loose ids come from. The specks it was
meant to remove fall from 121 to 33 a row, and blobs' cost is per pixel, not per region, so that
was never worth anything.

## Closing

Closing leaves every ant one region with its pixels intact and adds the pixels between its legs and
the specks within a kernel of it, area p50 185 to 227 at radius 1 and 260 at radius 2, which moves
the ants against max_area and the split's bounds but not against min_area. It does not mend the
gaps: 165 become 183 at radius 1 and 323 at radius 2, with the same median gap of one to two rows
and the same maximum near lost_rows, and the median loose id is shorter, 226 rows to 85, since a
closed ant touching another or the ramp's shade merges with it and the merged region is a new id
under track's step gate. The gaps the diagnostics finding counted are not a mask defect at the
ant's edge: an ant that vanishes for two rows leaves no pixels under 72 for a kernel to join, and
the gaps near 30 rows are ants at the cluster's edge absorbed into the region over max_area.
Whether the short gaps are lighting, blur or the ant's own luma rising is a question for the luma
plane, not the mask.

## What this says

On this clip at this scale morphology changes nothing for the better between threshold and blobs,
and an opening is harmful at any radius the kernel can take. The tool stays, since a mask from
inrange on a paint mark or a tag, docs/spec/identity.md's marks branch, is where a close fills the
hole a dot's highlight leaves and an open drops the single pixels a colour band admits, and nothing
there has been measured. It should not sit in the ants document.
