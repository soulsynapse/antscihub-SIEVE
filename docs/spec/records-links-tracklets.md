# Records, links, tracklets: what the detection and tracking tools promise each other

Read with the registry's type report (`python -m sieve_player.registry`), the live statement of what
feeds what, with `tools/_table.py`, which holds the table kind, and with docs/spec/identity.md, whose
identity pass this leaves in place and whose linker this replaces. Every tool and column word below
is a placeholder: docs/spec/tool-naming.md makes the words Kendrick's.

## Why

A fact a later tool needs is not recorded by the earlier one. A contact between two animals is
detection's fact, and `track`'s `merge_ratio` and `resolve.contacts` each derive it again from
centroids and boxes. `blobs`' filled contour is not the region's own pixels wherever the region has a
hole or a concavity (docs/findings/2026-11-12-blobs-contour-against-mask.md on `v5-runs`); `detect`
has no footprint, and `sample`, `attach` and `filter` read its box without saying so. `track` numbers
its ids from its walk's first row, and `resolve`'s labels file names a track by that number. None of
this is a better linker's to mend: docs/spec/blob-tools.md and identity.md both refuse one for want
of ground truth, and that stands.

The runtime decides the shape. A tool has one output. A series tool reads its one input and nothing
else, and its `step` is causal and is told no absolute row. A frame tool reads any row of its inputs
and any second plane. So a frame tool puts evidence on records and a series tool only associates
records across rows; whatever needs a plane or a neighbouring row sits before the linker. The wire
types stay `blobs` and `tracks`, and the contracts are `tools/_table.py`'s.

The tools this is shaped to admit, none of them a deliverable here: a tag detector with no mask, a
learned detector of boxes or keypoints, a tool that splits touching animals, an animal count per
record, a link by optical flow, a linker by a motion model under a global assignment, a stitch over
gaps, corrections from a file, a score against a reference, posture, patches, and records
interpolated over a gap. The table under What each coming tool asks says where each sits.

## How to read this

As identity.md's: each `##` below that carries boxes is a deliverable, with an `Assumes:` line, a
sentence of why, and done-when assertions, each a box with a `Check:` that is a one-off unless it
holds a seam or an invariant, by the Tests section of CLAUDE.md. A box is ticked by a session once
its check passes in the tree; a session never unticks or rewrites an assertion. Nothing here says
how. A deliverable lands with a finding on the crossings clip and the purb document beside the
baseline's.

## The chain as it stands, measured

Assumes: nothing.

Every later deliverable is read against the tools it replaces, on the same rows.

- [ ] A finding holds, for `blobs` and `track` as they stand on the crossings clip and the purb
  document, the records a row, the ids and their lengths, and the linker's own events as
  docs/findings/2026-11-01-track-diagnostics.md counts them.
  Check: a one-off under docs/findings/experiments.

## A record's name

Assumes: nothing.

`step` is told no absolute row, and a filter may sit between the tool that made a record and the
linker, so neither the row nor a record's place in its table names it.

- [ ] Every record carries a `key`, its row and its index in the table it was made in, unique
  within a table and kept by every tool that keeps records.
  Check: a seam: a table through `filter`, `sample` and `attach` has the keys it had.
- [ ] A tool that makes records gives each a key of its own, so two nodes' keys are never compared.
  Check: a one-off.
- [ ] A detector whose every input is static does not hand each row the first row's keys.
  Check: a one-off over a detector fed by a static mask.

## A record's footprint

Assumes: nothing.

A record made from a mask has pixels, one made from geometry has an outline, and one made by a
detector of boxes has neither; a reader is told which, and never given the box unasked.

- [ ] A record made from a mask carries its region as runs, and its footprint is the region's own
  pixels, holes kept.
  Check: a seam: a shape with a hole, its footprint against the mask it was found in.
- [ ] A record made from geometry carries a polygon, as `region.table`'s does, and its footprint is
  the polygon filled.
  Check: `tests/test_region.py` as it stands.
- [ ] A reader asking for a footprint of a record that has none raises, naming the column it
  lacks, unless it asked for the box.
  Check: a seam, in the same test.
- [ ] One tool makes records from a mask, with the position columns, the moment ellipse and the
  runs, in place of `blobs` and `detect`.
  Check: its records against `blobs`' on the two documents, a one-off.

## Links

Assumes: A record's name, A record's footprint.

Which records of the next row a record becomes is the footage's fact, and a contact is where the
answer is not one. Read off the pixels at this footage's frame rate it needs no model of motion.

- [ ] A frame tool adds to each record the key of the record of the row before it most overlaps
  and of the row after, and how many of each it overlaps at all, as flat columns; a record that
  overlaps none reads none.
  Check: a seam: two regions that merge and part, and the four columns at each row.
- [ ] A row's links are the same whichever row was asked for first, and the first and the last
  row read none before and none after.
  Check: the same seam, asked backwards.
- [ ] Two records overlapping by less than a knob's worth are not linked.
  Check: a one-off on the crossings clip, the passes that never merge.

## Tracklets

Assumes: Links.

A tracklet is one animal only if it spans no contact, and an id is a name only if a walk from
another row gives the same one.

- [ ] A series tool gives a record its predecessor's `id` where it has one predecessor and that
  predecessor one successor, and otherwise an id that is the record's own key; a predecessor the
  table before does not hold is none. `step` holds to `run`.
  Check: `tests/stepping.py`'s `hold`, and a seam: a merge and a parting make five ids, none
  across the contact, and a gated-out row ends every id.
- [ ] A walk begun at any row gives every tracklet born inside it the id a walk of the clip gives.
  Check: a seam: the linker stepped from two first rows.
- [ ] The tracks tables keep every column but the footprint and are flat.
  Check: `tests/test_columns.py` as it stands, and `held.py`'s `_flat` taking a tracks series whole.
- [ ] An edge of the graph is a link whose two ends differ in id, and one reading of a tracks
  series gives each id's rows, first and last records, parents and children; `tracks-filter`,
  `kinematics` and `resolve` read that and loop over no record of their own.
  Check: their tests as they stand.
- [ ] `kinematics`, `transitions`, `travel`, `csv` and the draw take the new ids.
  Check: their tests as they stand; `resolve.tables_of` reads an id past int32.

## A stitch

Assumes: Tracklets.

Overlap ends a tracklet wherever the detector drops a record, and on this footage that is every
few rows (docs/findings/2026-11-01-track-diagnostics.md, the reacquisitions outside the cluster).
What `lost_rows` did inside the linker is a pass over finished tracklets; how short the tracklets
are without it is not measured.

- [ ] A series tool, tracks in, tracks out, gives a tracklet beginning with no predecessor the id
  of one that ended with no successor within a reach in rows and in pixels, one to one, and never
  across a contact.
  Check: a seam: a record dropped for three rows is one id, and a record dropped beside a merge
  is two.
- [ ] The loose ants' tracklets on the purb document are no shorter than the baseline's.
  Check: the deliverable's finding.

## Identity over the edges

Assumes: Tracklets.

`resolve`'s elimination guesses a contact from where ids end and begin; the edges say it.

- [ ] `resolve` reads a contact from the edges, labels through one whose entering and leaving ids
  are as many, and flags and does not label through one the links counted as many to many.
  Check: `tests/test_resolve.py`'s merge and parting as it stands, and a seam for the refusal.

## The tools set aside

Assumes: every deliverable above.

- [ ] `blobs`, `detect` and `track` are not offered in the player, and identity.md, blob-tools.md
  and the README say what the tree has.
  Check: `python -m sieve_player.registry --check`.

## What each coming tool asks

| Tool | Where it sits | What it strains |
|---|---|---|
| A tag detector | a record with a polygon, a code and a heading | nothing |
| A learned detector of boxes | a record with no footprint | nothing |
| Keypoints, an embedding | columns of a record | `with_column` keeps no sub-array shape; an object column, or that mended |
| A background model | before the detector, mask out | nothing |
| A split of touching animals | a frame tool, records and a plane in, keys its own | it cannot read its own row before |
| An animal count | a frame tool by the row, or tracks to tracks by the run | nothing |
| A link by flow | a second frame tool writing the links' columns | nothing |
| A linker by a motion model | a second series tool writing `id` | nothing: an edge is a link across two ids |
| A linker by tag code | identity's, not a linker | nothing |
| Corrections from a file | identity's | see Open |
| A score against a reference | tracks and a path in, matched by position | a one-off first |
| Posture, patches | frame tools before the linker | patches are an object column |
| Records interpolated over a gap | tracks to tracks | a record said not to be observed |
| Pieces, a second camera | a piece at a time | this names no piece; docs/spec/pieces-of-footage.md's |

## Not settled by this

- A tracklet alive at a walk's first row has another id than the clip's until it ends, and a
  stitch adds its reach. The two boxes under A bout walked alone in pieces-of-footage.md are as
  open as they were, over fewer rows.
- The pile is one region that takes a new id at each contact with an ant at its edge, unless an
  area bound drops it before the links.
- A contact of many to many keeps its counts and loses the edges that are not the largest overlap.

## Non-goals

- A better linker. Gates, a calibrated step and a global assignment are identity.md's non-goals
  and stay so; this changes what a linker is told, not how well it guesses.
- Any tool in the table above.
- A change to `sieve_player`, beyond what A record's name's third box may ask.

## Open

- Every tool and column word here.
- Whether `mean`, `peak`, `core` and `split` go with `blobs`, `sample` reading the first three and
  a later tool doing the fourth; identity.md's Open asks the first half already.
- Whether a labels row names a row and a point, read against the footprint there, where it now
  names a track id that every upstream knob moves.
- Whether a saved document naming `blobs`, `detect` or `track` loads unresolved, as
  `tools/retired/` leaves it, or is lifted by `sieve_player/document.py` as crop2 was.
- The least overlap that links two records.
