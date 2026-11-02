# Identity: marks and codes attached to blobs, carried along tracklets, resolved after the fact

Prospective, 2026-11-01, none built. Read with the registry's type report (`python -m
sieve_player.registry`), the live statement of what feeds what, and with docs/spec/blob-tools.md,
which this shares three tools with and does not repeat.

## The measurements, and what each needs

The experiment is a colony emigration in the Pratt and Franks paradigm (Pratt, Mallon, Sumpter and
Franks 2002 and after), where individuals carry paint marks or printed codes and the video is scored
for three things. Ants per area is blobs in a region, which count and filter produce now. In and out
ratios are tracklets crossing a boundary, which needs a region and a per-row count of ids changing
side, and no identity. Identity coincidence is the third: an ant whose mark or code is read on some
rows is that ant on every row of the tracklet the read sits in, back to the tracklet's first row,
and through a merge and split by elimination where the graph forces it. That is the tracklet graph
with identity propagated through it, the structure every markerless or marked insect system uses
(idtracker.ai, TRex; with colour marks, anTraX, Gal, Saragosti and Kronauer 2020; with codes, Mersch,
Crespi and Keller 2013, Crall et al. 2015, Wild et al. 2018), and docs/findings/2026-11-01-track-diagnostics.md
is the measurement that says this footage needs it: the loose ants link cleanly between contacts and
every ambiguity is a contact. The alternative, assigning through contacts by motion, was tried the
same day on a bench and dropped, since nothing without ground truth could justify its numbers;
docs/spec/blob-tools.md says so where it lists what was measured.

The reason the whole thing rests on tracklets is that within one, identity is constant by
construction: the linker cut it wherever it was unsure, so one read anywhere labels the whole
tracklet in both directions, which is the back propagation asked for, and it is not inference. The
hard part, elimination through merges, is a post pass over finished tracklets, not a change to the
linker.

The marks are also the ground truth the linker lacked. A tracklet that ever carries two different
reads is a swap inside the linker, countable over hours with no human labelling, and that count is
the score any later change to track is judged on. Building the observation columns builds the
scoring harness.

## How the planes meet

Colour comes from one bgr decode of the full frame; the animal mask comes from whatever separates
the animals, threshold on gray, bg-subtract, or an inrange of its own; and each mark colour is one
inrange on the same frame. The mark masks overlap the animal mask by construction, since the mark is
on the animal, and that overlap is the whole mechanism: a mark's blob is attached to the animal blob
under it, and the animal's table gains the mark's columns. A code is printed on neon paper for the
same reason: its inrange finds the tag, blobs makes one record of it, the decoder runs on that record
alone, and the code attaches to the ant under it. The ant's blob never meets a tag detector.

Colour costs the bgr decode where the ants branch runs on luma; docs/findings/2026-11-01-luma-read.md
holds what that difference is on this machine. Identity means paying it, every row, since a read is
only as frequent as the frames it was looked for in.

## Two structural changes, before any tool

Tables must carry columns added downstream. blobs.DTYPE is fixed, filter and the exports read its
names, and nothing can add a column named by the user. Every tool below writes one, so the table's
own dtype, extended per tool, has to be what filter, size, track, travel and both csv tools read.
This is the change that makes an observation a column rather than a tool-specific side table, and
the reason the tools below can be general: none of them knows what a column means.

Tables must carry the shape of the plane they were found in. The record has none, and the spec's
blobs-to-mask was already blocked on it. Here it is what lets attach relate a table found at one
scale to a plane or table at another, which the neon tag at full resolution against ants at half is.

## The tools

Each is a module under tools/ with the facets the registry README names. Each is justified by the
measurement it serves and by the specific thing it would otherwise have been.

- **hsv** (frame; bgr in, hsv out). inrange converts the frame to HSV itself, so five mark colours
  are five conversions of the full frame a row. One conversion the memo shares is the difference
  between colour being affordable at full resolution and not; inrange accepts either input.

- **mask combine** (frame; two masks in, mask out: and, or, not, difference). A region is a mask
  from anywhere, a file, a painted blob, the difference of two; the animal mask under a bright mark
  is the dark threshold or the mark's own mask, since the mark is a hole in the silhouette
  otherwise. This is the one tool that makes "the region" and "the animal" compositions of what
  exists rather than new tools per case. Morphology, in docs/spec/blob-tools.md, is its neighbour for
  the hole a paint dot leaves.

- **blobs to mask** (frame; blobs in, mask out), in docs/spec/blob-tools.md. The nest region is the
  pile's own blob painted, which is how the boundary for in and out follows the pile when it moves.

- **sample** (frame; blobs and a gray or mask plane in, blobs out). A statistic of the plane inside
  each record's own mask, mean, max or nonzero count, into a column the user names. It is blobs'
  diff reading, which gives mean, peak and core now, made general and separable, and it serves what
  is not a blob: membership in a region mask, distance to a boundary from a distance transform.
  Colour counts could go through it too, but the dots and tags are blobs and attach says more about
  them.

- **attach** (frame; two blob tables in, the first out). Chosen columns of the second table written
  onto the record of the first that contains the second's centroid, or overlaps it most, with the
  second's centroid and area along. A paint dot attaches to the ant it sits on; a decoded tag attaches
  its code and heading; a region's blob attaches its id to every ant inside it. One tool for every
  "this blob is on that blob" relation, which is the whole of how a mark reaches an animal.

- **decode** (frame; blobs and a bgr or gray plane in, blobs out). Each record's box cut from the
  plane, scaled by the shape ratio, handed to an ArUco detector with a chosen dictionary; a code
  column and the tag's heading, since a code is read with its orientation and the moment ellipse's
  angle is ambiguous by 180 degrees. Its own tool because a code is read, not counted. Run on the
  neon mask's blobs, it decodes a few records a row rather than searching every ant, and a small
  dictionary with large inter-code distance keeps misreads rare and correctable. The thing to check
  before any of this is built is whether a tag decodes at all from a crop of this footage at full
  scale: a four-by-four code with its border is six cells and each cell wants several pixels, and
  which species this is decides the magnification.

- **transitions** (series; tracks in, signal out). Per row, the ids whose named column changed
  from one value to another since the row before, with a direction. Over a membership column from
  sample it is entries and exits, and the in and out ratio is two of these signals in csv. The
  boundary never enters the tracker, and the same tool counts any state change a column records.

- **tracks filter** (series; tracks in, tracks out), in docs/spec/blob-tools.md. Stubs out, and the
  tracklets resolve reads restricted to confirmed ones.

- **resolve** (series; tracks in, tracks out). The identity pass. Takes the names of the observation
  columns, colour counts, codes, or a labels file through a path input as a human source, and
  writes an identity column: a tracklet is labelled only from several reads agreeing with none
  contradicting, so one false decode cannot relabel a tracklet back to its birth; identity is
  exclusive in time, so a tracklet overlapping a confirmed sighting elsewhere cannot be that
  animal; elimination runs through merges and splits. A tracklet with two different reads is left
  as the swap it is and counted, which is the linker's score. It has a series face over the window
  and a file face over the tracks csv, as csv has two faces, because back propagation across
  minutes only works over the whole export. It is general in that it never knows what an
  observation is, only that a column asserts an identity, and the labels file is how the manual
  method's scoring and the human corrections enter the same pass.

Two changes to what exists. track cuts a tracklet at a merge or split, a blob whose area jumps past
a ratio of the track's own ending the tracklet rather than continuing it, so that a tracklet is one
animal by construction and one read may label all of it; the cut is the only linker change this
needs. And filter, size, travel and both csv tools read the table's dtype, not blobs.DTYPE.

## What this does not need

Gates on area, sides, a stitch, a calibrated step, Hungarian assignment. The marks and codes carry
identity; the linker only keeps its tracklets honest, and the count of tracklets carrying two reads
is what says whether it does.

## Order

The dtype and plane-shape changes; hsv and mask combine; sample and attach, which make the first
quantity's regions and the second's crossings possible with transitions; decode, after the
resolution check on real tags; resolve last, since it needs columns to read and the export to run
over. Each tool lands with a finding on the marked footage that says what it read, as blobs did.
