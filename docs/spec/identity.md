# Identity: marks and codes attached to blobs, carried along tracklets, resolved after the fact

Prospective, 2026-11-02, none built. Read with the registry's type report (`python -m
sieve_player.registry`), the live statement of what feeds what, and with the facet table in the
root README, which says what a tool may declare. docs/spec/blob-tools.md lists the rest of what the
blob branch lacks; two of its tools are deliverables here because the ones below assume them.

## Why

The experiment is a colony emigration in the Pratt and Franks paradigm (Pratt, Mallon, Sumpter and
Franks 2002 and after), where individuals carry paint marks or printed codes and the video is scored
for three things. Ants per area is blobs in a region. In and out ratios are tracklets crossing a
boundary, and need no identity. Identity coincidence is the third: an ant whose mark or code is read
on some rows is that ant on every row of the tracklet the read sits in, back to its first row, and
through a merge and split by elimination where the graph forces it. That is the tracklet graph with
identity propagated through it, the structure every marked or markerless insect system uses
(idtracker.ai, TRex; with colour marks anTraX, Gal, Saragosti and Kronauer 2020; with codes Mersch,
Crespi and Keller 2013, Crall et al. 2015, Wild et al. 2018). docs/findings/2026-11-01-track-diagnostics.md
is the measurement that says this footage needs it: the loose ants link cleanly between contacts
and every ambiguity is a contact. Assigning through contacts by motion was tried the same day and
dropped for want of ground truth; docs/spec/blob-tools.md says so.

Within a tracklet identity is constant by construction, since the linker cut it wherever it was
unsure, so one read anywhere labels the whole tracklet in both directions. That is the back
propagation asked for and it is not inference; elimination through merges is the inference, and
it is a pass over finished tracklets, not a change to the linker. The marks are also the ground
truth the linker lacked: a tracklet carrying two different reads is a swap inside the linker,
countable over hours with no human labelling, and that count is what any later change to track is
judged on.

The planes meet like this. Colour comes from one bgr decode of the full frame; the animal mask
from whatever separates the animals; each mark colour is one inrange on the same frame, and its
mask overlaps the animal mask because the mark is on the animal. A mark's blob attaches to the
animal blob under it and the animal's table gains the mark's columns. A code printed on neon paper
is found the same way, so the decoder runs on the tag's record alone and the ant's blob never
meets a tag detector. Identity therefore costs the bgr decode on every row where the ants branch
runs on luma; docs/findings/2026-11-01-luma-read.md holds that difference.

## How to read this

Each `##` below is a deliverable: an `Assumes:` line naming what it builds on, a sentence of why,
then done-when assertions, each a box with a `Check:` that is a test in `tests/`. A box is ticked
by a session once its test passes in the tree; a session never unticks or rewrites an assertion,
and before building toward an unticked box checks whether the tree already meets it. Where a
result is worth Kendrick's eye before the next deliverable leans on it, a `Worth a look:` line says
what to look at; it is not a gate. Nothing here says how. Any deliverable whose `Assumes:` are all
done is available; among those the earlier one in the file first.

## Columns a table carries

Assumes: nothing.

Every tool below writes a column the user names, and nothing can today: blobs.DTYPE is fixed and
filter, size, travel and both csv tools read its names. A table that carries its own columns is
what makes an observation a column rather than a side table, and what lets the tools below be
general: none of them knows what a column means.

- [x] A tool downstream of blobs adds a column, named by its params, and the table reaches filter,
  size, track, travel, tracks-csv and draw with that column in it; track's output has the column
  beside `id`; tracks-csv writes it.
  Check: a test adds a column with a stub tool and reads it through each of those.
- [x] filter's `field` offers the table's own columns, so a column added upstream is a field to cut
  on, and the ratios it computes still are.
  Check: a test filters on an added column.
- [ ] A column added under a name the table already has is reported on that node, as a type
  mismatch is, and the table passes through unchanged.
  Check: a test adds `area` and reads the report.
- [x] blobs' own columns, their names, types and `contour` as an object column, are as they were,
  and every existing test passes.
  Check: `tests/test_blobs.py` and `tests/test_track.py` unchanged and green.

## The plane a table was found in

Assumes: nothing.

A record carries no frame shape, which blocked blobs-to-mask already. Here it is what lets a table
found at one scale meet a plane or a table at another, which a neon tag at full resolution against
ants at half is.

- [x] A blobs table carries the height and width of the plane it was found in, and the shape
  survives filter, track and every tool that passes a table through.
  Check: a test reads the shape off blobs' output and off track's.
- [ ] A tool that relates a table to a plane or table of a different shape does so in the other's
  coordinates, scaling by the ratio of the shapes, and the result reads the same whether the
  table or the plane was the larger.
  Check: a test runs sample (below) on a plane at twice the table's shape and at half, and reads
  the same column.

## hsv

Assumes: nothing.

inrange converts the frame to HSV itself, so five mark colours are five conversions of the full
frame a row; one conversion the memo shares is what makes colour affordable at full resolution.

- [ ] A frame tool, bgr in, hsv out, whose output inrange accepts beside bgr, and inrange's mask is
  the same from either.
  Check: a test runs inrange on a bgr frame and on hsv of it and compares the masks.
- [ ] Several inrange nodes reading one hsv node cause one conversion a row.
  Check: a test with three readers asserts one run of hsv per row, through the probe.

## Mask combine

Assumes: nothing.

A region is a mask from anywhere, and the animal under a bright mark is the dark threshold or the
mark's own mask, since the mark is a hole in the silhouette otherwise. One tool makes "the region"
and "the animal" compositions of masks that exist rather than a tool per case; morphology, in
docs/spec/blob-tools.md, is its neighbour for the hole a paint dot leaves.

- [ ] A frame tool, mask in with a second mask input, mask out, with a method among and, or,
  difference, and not, where not reads the first input alone and the second may be unwired for it.
  Check: a test for each method on two small masks.
- [ ] Two masks of different shapes are reported on the node, as a type mismatch is, and the
  node computes as None.
  Check: a test wires mismatched shapes and reads the report.

## Blobs to a mask

Assumes: The plane a table was found in.

The nest region is the pile's own blob painted, so the boundary for in and out follows the pile.
Listed in docs/spec/blob-tools.md; a deliverable here because sample and transitions assume it.

- [ ] A frame tool, blobs in, mask out, the plane's shape, with every record painted by its
  contour or its box by a knob; a table with no records is an empty mask.
  Check: a test paints a known table and compares to the mask blobs was run on.

## Sample

Assumes: Columns a table carries, The plane a table was found in.

blobs reads a second plane inside each record now, its diff input giving mean, peak and core; this
is that reading made general and separable, into a named column, for what is not a blob:
membership in a region mask, distance to a boundary from a distance transform.

- [ ] A frame tool, blobs in with a gray or mask plane as a second input, blobs out with one
  column added, named by the params, holding a statistic of the plane inside each record's own
  mask, not its box: mean, max, or count of nonzero pixels, by a knob.
  Check: a test with a plane holding a known patch under one record and nothing under another.
- [ ] A plane of a different shape from the table's is read in the plane's coordinates.
  Check: the test under The plane a table was found in.
- [ ] Sampling a mask painted by blobs-to-mask from a region's table gives a membership column
  that reads full inside and empty outside.
  Check: a test paints one record and samples a table with records in and out of it.

Worth a look: a region mask and a membership column on the ants clip, since what counts as inside
the nest when an ant straddles its edge is a choice between mean and count that the footage decides.

## Attach

Assumes: Columns a table carries, The plane a table was found in.

Every "this blob is on that blob" relation: a paint dot on the ant it sits on, a decoded tag's code
and heading on the ant under it, a region's blob on every ant inside it. The mark's own centroid
and area come along, which a pixel count does not say.

- [ ] A frame tool, blobs in with a second blobs input, the first table out with columns of the
  second written onto the record the second's centroid lies in, by contour or box by a knob; the
  columns are named in the params and land under a prefix the params give, with the second's
  `cx`, `cy` and `area` always among them.
  Check: a test attaches a small table of dots to a table of animals and reads each dot's
  columns on the right animal.
- [ ] A record with no attachment reads NaN in the attached columns, and one with several reads
  the largest by area with a count column saying how many.
  Check: a test with an animal under no dot and one under two.
- [ ] Tables found in planes of different shapes attach in the first table's coordinates.
  Check: a test attaches a table at twice the shape.

Worth a look: a colour's inrange blobs attached to the ants on marked footage, before decode is
built, since it is the same path and shows whether the dot's blob survives the animal threshold.

## Decode

Assumes: Attach.

A code is read, not counted, so it is its own tool; run on the neon mask's blobs it decodes a few
records a row rather than searching every ant. The tag's orientation comes with its code, where the
moment ellipse's angle is ambiguous by 180 degrees.

- [ ] A frame tool, blobs in with a bgr or gray plane as a second input, blobs out with a code
  column and a heading column in degrees, from an ArUco detector over each record's box cut from
  the plane with a margin, under a dictionary chosen by a knob; a record that decodes to nothing
  reads none in both.
  Check: a test draws a marker into a plane, finds it with blobs, decodes it and reads its id and
  heading; a record over blank plane reads none.
- [ ] A plane of a different shape from the table's is cut in the plane's coordinates.
  Check: a test decodes from a plane at twice the table's shape.

Worth a look: before this is built at all, whether a tag decodes from a crop of real footage at
full scale; a four-by-four code with its border is six cells and each cell wants several pixels,
and the species and magnification decide it. If it does not decode, this deliverable waits on the
rig, not on the code.

## Transitions

Assumes: Columns a table carries.

Entries and exits are ids whose membership changed between consecutive rows; the boundary never
enters the tracker, and the same count serves any state a column records.

- [ ] A series tool, tracks in, signal out: per row, the ids present in it and the row before
  whose named column changed, from a value to a value given in the params, either blank for any.
  An id absent in the row before counts nothing.
  Check: a test with a synthetic track table whose ids cross a membership column, and a second
  node with from and to swapped reads the exits.

## Tracks filter

Assumes: Columns a table carries.

Stubs out, and the tracklets resolve reads restricted to confirmed ones. Listed in
docs/spec/blob-tools.md; a deliverable here because resolve assumes it.

- [ ] A series tool, tracks in, tracks out, keeping the ids whose property lies in a range with
  filter's blank-is-none bounds: rows seen, net displacement, path length, or the mean of a
  named column. Ids are not renumbered; a dropped id's records leave every row.
  Check: a test drops a short track and a far-walking one and reads the ids left.

## A tracklet is one animal

Assumes: nothing.

One read may label a whole tracklet only if a tracklet never spans a contact. The linker's step
gate mostly ends a track at a merge already, since a pair's centroid is far from either; the cut
on area makes it a rule rather than a property of this footage, and it is the only change to the
linker this needs.

- [ ] track ends a track rather than continuing it onto a blob whose area is over a ratio of the
  track's own, the ratio a param, the track's own area a running estimate over its rows; the merged
  blob is a new id, and the pieces it splits into are new ids.
  Check: a test with two animals merging into one blob and parting: five ids, none shared across
  the merge.
- [ ] With the ratio off, track's ids are what they were.
  Check: `tests/test_track.py` unchanged and green.

Worth a look: the ratio on the crossings clip, since a flickering blob at the pile's edge can trip
an area cut as a merge does.

## Resolve

Assumes: Attach, Transitions, Tracks filter, A tracklet is one animal.

The identity pass. It never knows what an observation is, only that a column asserts an identity,
so colour counts, codes and a labels file enter it alike, and the manual method's scoring and a
human's corrections are the same source as a tag.

- [ ] A series tool, tracks in, tracks out with an identity column, reading observation columns
  named in the params. An id is labelled from reads on its own rows only where at least a number
  of reads agree, the number a param, and none contradict; a labelled id is that identity on every
  row it holds, before and after the reads.
  Check: a test with one read on a long tracklet reads the identity on its first row; a test with
  fewer reads than the number reads none.
- [ ] An id with reads of two identities is labelled neither and flagged in a conflict column; the
  node's signal is the identities present per row or the conflicts per row, by a knob.
  Check: a test with a swapped tracklet reads the flag and the signal.
- [ ] Identity is exclusive in time: an id overlapping in rows with a labelled id of the same
  identity is not that identity, whatever it reads.
  Check: a test with two ids both reading blue over overlapping rows resolves the better supported
  and flags the other.
- [ ] Through a merge of a labelled id and an unlabelled one into one id that splits into two,
  a read on one piece labels the other by elimination.
  Check: a test with purple and unknown merging, parting, and blue read on one piece; the other
  reads purple back to its first row.
- [ ] A labels file, rows of row span, track id and identity, enters through a path input as reads
  of a further column, and resolves as any other.
  Check: a test wires a selector to a labels file beside the document.
- [ ] The same pass runs over a tracks csv written by tracks-csv, from the command line, and writes
  the file back with the identity and conflict columns, so back propagation spans the whole export
  and not the window.
  Check: a test writes a tracks csv, resolves it, and reads the columns back through csv's key line
  intact.

Worth a look: the conflict count per row on marked footage, since that count is the linker's score
and the first number this whole spec exists to produce.

## Non-goals

- Assigning identity through a contact by motion: gates on area, sides, a stitch, a calibrated
  step, Hungarian assignment. Each was tried on 2026-11-01 against the clip's own counts or a
  simulation built to the same assumptions, none could be justified without ground truth, and the
  marks make them unnecessary: the linker only has to keep its tracklets honest.
- Identity by appearance. At this resolution an ant carries nothing to learn, and the wasp
  benchmark (WaspMOT, Stanczyk et al. 2026) found the same for small identical insects; marks and
  codes are the observation.
- A labelling mode in the GUI. The labels file through a path input is the same source, and what a
  labelling mode should record is not known until the file face of resolve has run on real
  footage and said where the conflicts are.
- Per-blob image patches as a column. Nothing here consumes them; decode cuts its own crop.

## Open

- Whether blobs' diff reading, its `mean`, `peak` and `core` columns and the split that uses them,
  is retired into sample once sample exists, or stays as the one case fast enough to live inside
  blobs. A finding on the ants clip decides it.
- Whether a paint dot goes through attach, as a blob of its own, or through sample, as a pixel
  count inside the animal, which is one fewer blobs pass per colour. The argument for attach is
  the dot's own centroid and area; the footage decides whether that is worth the pass.
- The animal mask under a bright tag, which is a settings question per marking scheme (threshold
  or combined with the tag's mask) and not a tool, until a marked clip shows it is.
- Whether resolve runs in the GUI window at all, or only over the export. The series face shows
  identities on the canvas while scrubbing, which is what makes a marking scheme tunable by eye;
  the file face is what the measurement comes from.
