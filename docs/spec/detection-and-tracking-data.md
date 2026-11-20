# Detection and tracking data

Read with `docs/spec/pieces-of-footage.md`, whose piece's record Part 2 leans on
and whose question of a bout walked alone Part 5 takes up; with
`docs/spec/identity.md`, which built the tools Part 3 sorts; and with the
registry's type report (`python -m sieve_player.registry`), the live statement of
what feeds what.

## How to read this

No deliverable is here and no box: a session builds nothing from this file.
Part 1 is a model of what detection and tracking data is; it mentions nothing of
SIEVE and stands without it. Part 2 is how SIEVE carries the model, and what of
the runtime has to change to carry it. Part 3 sorts the present tools against
the model. Part 4 sets this beside the earlier attempt. Part 5 holds the choices
that are Kendrick's, each with a recommendation and none settled. Part 1 can be
accepted and Part 2 rejected, or the reverse.

Every name of a thing, a column or a tool here is a placeholder. What Parts 2 and
3 say of the tree is as it was read, cited by file and name, and is verified
against the tree before anything leans on it.

## Part 1. The model

### 1.1 One case, carried through

Two loose ants, P and Q, walk on a clean floor. P carries a printed tag. For
frames 0 to 99 a detector reports two blobs a frame. From 100 to 139 the ants
touch and the detector reports one blob. From 140 on it reports two again. At
frame 150 the tag on one of the two is read.

What is known without inference is five runs of blobs: two before, one during,
two after. What is inferred, in rising order of how much is assumed: that the
one blob holds two animals; that each blob after is one of the animals before;
which is which. The tag settles the last for frames 140 on, and, if ants neither
appear nor vanish, for frames 0 to 99 as well. Where exactly P was inside the
shared blob at frame 120 is never observed; any coordinate given for it is an
estimate.

A representation is judged here by whether it can hold each of those statements
apart from the others, so that a later tool can take the first without being
handed the last.

### 1.2 How the fields that have solved this carry it

Each was read for this document unless marked. Where a source was not reached
the mark says so, and nothing below rests on an unreached source alone. The
reading was through a summarising fetch, so a quotation is as that reader gave
it; the Cell Tracking Challenge's document was read directly.

| Format | A row is | Identity is | Two animals in one detection | A detection nobody claimed | Absence |
|---|---|---|---|---|---|
| MOTChallenge (MOT16 paper) | one box of one target in one frame | a column on the row | cannot be said; each target keeps its own box through occlusion "if the position can be determined unambiguously" | `-1` in the identity column, in detection files only | `-1` |
| Cell Tracking Challenge (conventions document) | a labelled region in a per-frame label image, and one `L B E P` line a track | the label, "propagated over time" | cannot be said; each track has one parent `P` | a segmentation-only file, whose labels are "not necessarily propagated over time" | label `0`, parent `0` |
| TrackMate, after the LAP tracker of Jaqaman and others (TrackMate documents; the 2008 paper not read) | a spot; an edge; a track | membership of a connected graph | a merge edge, read in u-track as two particles that overlap; TrackMate's page says its author has not met one in life-science data, and reads a split as a division | a spot with no edge | no row |
| GEFF (specification) | a node; an edge `(source, target)`; a property array beside them | not a type: `tracklet` and `lineage` are node properties the file declares | a node with more than one edge in; the specification neither allows nor forbids it | a node with no edge | a `missing` mask beside every property |
| idtracker.ai (output page; pipeline from summaries of the papers, not the papers) | a blob, classed individual or crossing; a fragment; then a dense `(frames, animals, 2)` array | an index into a roster of known size | the crossing class; the output has no position there, or an interpolated one | not in the output | `NaN`; probability `0` |
| TRex (formats page) | one file an individual, one entry a frame | the file | not in the output | not in the output | `missing = 1`, values `infinity` |
| anTraX (paper, first two fifths) | a blob; a tracklet, "linked blobs in consecutive frames that are composed of the same group of individuals"; a node of a directed acyclic tracklet graph | a set of assigned IDs and a set of possible IDs on each tracklet | a multi-animal tracklet, with a set of IDs | an unidentified tracklet; labels `Unknown` and non-ant | a gap in the per-ID table |
| SLEAP, sleap-io (model page) | an instance, a centroid, a box or a mask, owned by a frame | two fields on the instance: `track`, which "links the same animal across frames", and `identity`, a "cross-session persistent animal identity" | cannot be said | an instance with no track | `NaN` points |
| FORT myrmidon (API pages) | a tag reading; an `Identification` of a tag with an ant over `[Start, End)` | an `Ant`, apart from any tag | not applicable, tags do not merge | a tag with no identification | no row |
| movement; NWB ndx-pose (documents) | a cell of `time × space × keypoint × individual`; a series a body part | an axis; a file | cannot be said | cannot be said | `NaN` |

Where each was read: ar5iv.labs.arxiv.org/html/1603.00831;
public.celltrackingchallenge.net/documents/Naming%20and%20file%20content%20conventions.pdf;
imagej.net/plugins/trackmate/trackers/lap-trackers;
liveimagetrackingtools.org/geff/latest/specification;
idtracker.ai/latest/user_guide/output_structure.html; trex.run/docs/formats.html;
pmc.ncbi.nlm.nih.gov/articles/PMC7676868; io.sleap.ai/latest/model;
formicidae-tracker.github.io/myrmidon/latest/api/python/ant_identification.html;
movement.neuroinformatics.dev/latest/user_guide/movement_dataset.html;
github.com/rly/ndx-pose. DeepLabCut's multi-animal output was looked for and its
layout not found, so it is not in the table.

Three things recur wherever the animals touch, and are missing wherever the
format assumes they do not. A detection is kept apart from the animal: anTraX's
blob, idtracker.ai's blob, the Cell Tracking Challenge's segmentation-only file,
MOTChallenge's detection file. What joins detections over time is a graph and
not a column: GEFF, TrackMate, anTraX, and the Challenge's "acyclic graph for the
whole video". Who the animal is stands apart from what follows what: SLEAP's two
fields, myrmidon's `Identification`, anTraX's sets of IDs laid over its graph.
The dense arrays of movement, idtracker.ai and TRex are what is left after all
three have been decided; they are an output and not a place to keep the deciding.

The metrics say the same. HOTA (Luiten and others; read in summary, not the
paper) scores detection, association and localisation apart because a tracker
can be good at one and bad at another, which is only measurable if the data can
hold them apart.

From recall, not checked: tracking as a minimum-cost flow over a graph of
detections (Zhang, Li and Nevatia; Berclaz and others), in which a track is a
unit of flow and an occlusion is a node carrying more than one; multiple
hypothesis tracking (Reid), in which rival associations are kept until evidence
chooses; Ultrack and its relatives (read in summary), in which rival
segmentations of one cell are kept in a hierarchy and a solver selects among
them. The model below is the flow reading.

### 1.3 What exists

**A recording.** Footage with a clock and a pixel grid. A time is a frame of one
recording; the recording says what instant a frame is. A place is a point on one
recording's grid; a calibration, where there is one, takes it to the floor.

**An observation.** A claim by one producer that at one time, over one extent of
one recording, there is something. Its extent is as fine as the producer could
make it: a point, a box, an outline, a set of pixels. It is not an animal. It may
hold none, one, part of one, or many, and it does not say which.

**An observation set.** All the observations one producer made, with its
coverage: the times and the part of the grid it looked at. A covered frame with
no observation says nothing was found; a frame outside the coverage says nothing
at all. An observation is named within its set and nowhere else. A set made again
with any difference is another set, and no name carries over.

**A measurement.** A value a producer gives to each member of some set: of an
observation set, of the edges of a relation, of a roster. An area, an
orientation, a class, a tag code, a score for a paint colour, a vector from an
appearance network, a set of keypoints under a skeleton, an estimate of how many
animals an observation holds. Each measurement is its own thing beside the set
and names its producer, so two producers can measure the same quantity and
disagree. A member with no value is marked as having none; no value of the
quantity's own range stands for absence.

**A link.** A directed edge from an observation to a later one of the same
recording, claiming that at least one animal in the first is in the second. It
may pass over frames. A link set is the edges one producer claimed over one or
more observation sets; edges carry measurements as observations do, among them a
cost and a flow, the number of animals the edge is claimed to carry. More than
one edge into an observation is a meeting, more than one out a parting. A link
set states which shapes it keeps to, and the type keeps to none: one that allows
at most one edge in and one out is what MOTChallenge calls tracking; one that
allows one in and two out is a lineage; one dense with rival edges and their
costs is a candidate graph, and the selection a solver makes from it is another
link set.

**A containment.** An edge between two observations of the same time, usually of
different sets, claiming that what the first shows is
within or is part of what the second shows. A tag reading within a body. A head
point within an outline. A body cut out of a blob by a second pass, within that
blob. Two halves of an animal the detector split at a paint mark, within the one
body a later pass made of them.

**A tracklet.** A longest run of observations joined by links with no meeting or
parting inside it. It is computed from a link set and holds nothing the link set
does not. It is the unit over which evidence is pooled, because within it the
animals are by construction the same ones.

**An individual.** An animal, standing apart from every observation of it. A
roster is a set of individuals and says how it came by them. A declared roster is
written by a person: these forty ants, named. A minted roster is made by a
producer that has decided some paths through a link set are each one animal; its
individuals are named within it and nowhere else, as observations are within
their set. A roster says whether it is closed, meaning no animal exists outside
it, and over which recordings one of its individuals is the same animal.
Individuals carry measurements, which may hold over an interval of time rather
than always.

**A key.** A declared table saying that a marker value, a tag code or a colour
class, means an individual over an interval of time. Two rows for one marker may
not overlap in time, nor two rows for one individual under one kind of marker.
This is myrmidon's `Identification`.

**An assignment.** A weighted relation between an individual and an observation:
this animal is in this observation, to this degree. Many to many. An observation
may carry several individuals; an individual may carry several observations of
one time, when the detector split it or when the weights are a spread over
candidates. An assignment set is what one producer decided, from one link set,
one roster, and whatever evidence and keys it read.

**A track.** For one individual, a value at each time: where, facing which way,
in what pose, each with a kind that says how it was come by. Observed alone, from
an observation assigned to that individual only. Observed shared, from an
observation holding others too, so the place is the group's. Estimated, from no
observation of that time. Absent. Each value names the observation it was drawn
from where there was one. A track is computed from an assignment set, the
measurements it reads, and an estimator.

**A hand statement.** What a person says, anchored to the footage and never to a
name inside a derived set: at this frame, the thing at this place is this
individual; the thing here and the thing there, a frame apart, are not the same;
there is an animal here that no detector found. A statement is resolved against
whichever observation set is current, and it is an input to producers, which
keep to it; it is not an edit of what they produced.

### 1.4 What refers to what, and what is derived

```
recording
  └─ observation set ──────────── coverage
       ├─ measurement             (one or many, each with its producer)
       ├─ containment             (to another set's observations, same time)
       └─ link set                (edges, with their own measurements)
            ├─ tracklets          (computed, nothing new)
            └─ assignment set ─── roster, key, evidence
                 └─ tracks        (computed, with an estimator)
hand statements ── anchored to the recording, read by any producer above
```

Every arrow of reference points up this figure. An observation knows nothing of
links; a link set knows nothing of individuals. A producer lower down may make a
new thing higher up, a second observation set cut from the first using what the
links showed, with containment back to the first; the result is a new set with
its own links below it, never a change to the one it started from. The figure is
an order of reference and not a fixed order of stages.

A producer's result depends on its input over one of three reaches, and the
reach is part of what the result is. A frame's: the observations of frame *t*
from frame *t*. A history's: a filter and assignment tracker's links at *t* from
everything before *t*. A span's: an identity solved over a whole graph, a
classifier trained on the tracklets it will then label. A result of the second
or third reach does not exist a frame at a time; it exists for a span, and
changes when the span does.

In the case of 1.1: one observation set, five tracklets. A link set with a
meeting at frame 100 and a parting at 140. A measurement of two on the shared
tracklet's observations. A tag measurement on one observation at 150, a key
taking the code to P, a declared closed roster of P and Q. An assignment set
giving P to the tagged tracklet and, since the roster is closed and nothing
appeared or vanished, to one tracklet before, Q to the others, both to the
shared one. Two tracks whose values for 100 to 139 are of the shared kind. Take
away the tag and the roster and everything down to the link set stands unchanged;
the assignment before and after the touch then becomes two weights of a half, or
a minted roster of four animals that makes no claim across the touch.

### 1.5 The choices, with what was turned down

**An observation is not an animal.** Turned down: the row that is one target at
one time (MOTChallenge, SLEAP's instance, the dense arrays). It cannot say the
shared blob of the case, nor the pile, nor a blob that is a dropped seed. It can
be had from this model, as the observations assigned one individual each. This
model cannot be had from it.

**How many animals an observation holds is a measurement, not its type.** Turned
down: two kinds of blob, single and crossing (idtracker.ai), or single and multi
tracklets (anTraX). The count is an inference, by area, by a classifier, or by
solving the flow, and inferences disagree and get revised; a type cannot be held
twice. A pile wants a number with an error, not a class.

**Association is a graph of edges, not an identity column and not a table of
tracks with a parent.** Turned down: MOTChallenge's column, which has no meeting;
the Challenge's `L B E P`, which has partings and no meetings because a track has
one parent. Ants meet. The graph holds both of the others as link sets of
restricted shape. What it costs: every consumer that wanted a plain track must
say which paths it means, which is the next choice.

**Identity is a relation laid over the graph, not a property of observations or
of tracklets.** Turned down: identity as a field of the observation (SLEAP,
MOTChallenge), which cannot hold two animals, a set of candidates, or two
producers' rival answers, and which rewrites the observations to change its
mind. Turned down: assignment to tracklets (anTraX, idtracker.ai's fragments).
It is what a solver will mostly produce, and an assignment constant along a
tracklet says it exactly; but a tracklet is only as right as its links, and an
identity that changes inside one, which is what a wrong link looks like once a
tag is read on both sides of it, has nowhere to go. The model relates
individuals to observations; whether the carrying of it is a row a run is Part
2's.

**One kind of individual, with the roster saying how far its sameness reaches.**
Turned down: SLEAP's two, a track for the recording and an identity across
sessions. Its track is either a tracklet, which is computed, or an individual of
a roster that reaches one recording; a third kind adds nothing that can be said.

**What a marker means is declared apart from the reading of it.** Turned down:
the tag code as the animal's name. Tags fall off and are put on another ant; a
colour is reused in the next colony. Myrmidon's separation is taken whole.

**A track is computed and says how each value was come by.** Turned down: the
dense array as the store (idtracker.ai, TRex, movement). It cannot say which
observation a value came from, that a place is a group's, or that an observation
went unclaimed. As an output it is what most analysis wants and is one
projection of a track.

**Hand statements are anchored to footage.** Turned down: a correction that names
a tracklet or an observation. It is exact and cheap, and it is void the moment
the detector's threshold moves, which is when corrections are most wanted.
Anchoring costs a resolving step and can fail to resolve, when nothing is found
at the place named; that failure is reported, since it means the statement and
the detection disagree.

**Absence is marked, and coverage is stated.** Turned down: the sentinels, `-1`,
`0`, `NaN`, `infinity`, each of which is a value of the quantity somewhere. No
row within coverage, no row outside coverage, and a row with no value are three
facts.

**Parts and rival readings are observation sets joined by containment, not
fields inside an observation.** Turned down: a fixed observation with slots for
box, outline, keypoints and tag. Each slot is a producer that may be absent,
doubled or replaced, and a keypoint finder that works before any body is found
has no body to put its slot in. What it costs: a join where a slot would have
been a lookup.

### 1.6 What the model cannot hold

An observation is of one time, so a thing detected only as a streak over several
frames is a run of observations with links made together by one producer, not
one thing. An observation is of one recording; the same animal seen by two
cameras at once wants a third kind of edge, which is not here. Individuals
neither divide nor fuse; a brood item becoming a worker, or a lineage, wants a
relation between individuals, which is not here. Place is on the image grid;
depth in a pile is not held, and an animal under another is unobserved, not
occluded at a known depth. Flow read as animals an edge carries is wrong across
frames where a detector has split one animal in two, until a later set joins the
halves. None of these is shut out by a choice above; each is a further relation
beside the ones given.

### 1.7 What paper does not decide

Whether a count needs an error or a whole distribution over it: decided by the
first analysis of a pile, by whether its answer moves when the count's spread is
dropped. Whether containment must be stored or can always be computed from two
extents: stored is needed only for a producer whose parts have no extent, a
keypoint finder; decided when one is wanted. Whether identity can be recovered
through a pile at all: decided by measuring, on tagged footage, the share of
frames in which a tag inside the pile is read, since below some share a
candidate set never narrows and the weights are decoration. Whether one
recording's frames are regular enough that a link's gap in frames is a gap in
time: decided by the recordings' own timestamps.

## Part 2. How SIEVE carries it

### 2.1 The runtime, as read

A node is a frame node or a series node (`registry.kind`). A frame node's value
at a row is computed from its inputs at rows and kept by key and row
(`graph.Graph._compute`); it reads as many named inputs as its tool declares
(`INPUTS`). A series node's value is over the rows a walk covers
(`walk.run_chain`). It reads one node (`plan.Entry.src`). Every series node hangs
from one frame node, the walked one, and one that reads another frame node is not
run (`plan._standing`). A frame node cannot read a series node:
`Graph._compute` answers None for one.

A series result is a dict of fields, each a value a row; `held.good` takes one
for a result only with a `signal` in it, and the next node is fed the signal or
the `rows` under the band and no other field (`graph.gated`). A table is a
structured array a row, "one record a region" (`wire.Type`), with the plane it
was found in and each column's unit on its dtype (`tools/_table.py`).

A series tool is stepped a row at a time where it offers `step` and everything
above it on the chain steps, and is otherwise run whole over the rows so far at
each cadence row (`docs/spec/solver.md`). `step` is handed the row's place in the
walk's range and not in the footage (`walk._Walk.step`). A stepped node's value
at a row can depend on where its walk began, so two walks' rows are not stitched,
and a window is served from a held run only by cutting rows out of it
(`docs/spec/held-results.md`). A walk stops where its stack and stepped results
pass `walk.STACK_BYTES`.

What a person made reaches a tool as a file on a path input, whose loader's
answer is laid on the node's params and so lies in its key
(`sieve_player/registry/README.md`; `tools/resolve.py`'s `PATHS`).

### 2.2 The carrying

| The model's | Carried as | The tree has |
|---|---|---|
| recording, time, place | the footage; a row, numbered by `decoder`'s `frame_times`; a table's plane; a piece's record | all but the record, which `docs/spec/pieces-of-footage.md` specifies and which is not built. Without it a table below a `region` is in the cut's pixels and no place in it can be laid on the footage |
| observation set | a frame node's table a row, each record with a serial its producer mints and nothing renumbers. An observation's name is the node's key, the row and the serial | the table. No serial: a record is known by its position, which `filter` and `tracks-filter` change |
| coverage | in time the rows a run holds, an empty table being a row looked at; in space the piece | both, the second with the record |
| measurement | a column, minted with its unit through `with_column` under a prefix that says whose it is. A float column marks absence by NaN; a column of whole numbers that can be absent is carried as float | this, as `docs/spec/identity.md` built it. `blobs`' `core` reads -1 and `track`'s `id` -1 for none |
| count of animals | a measurement like any other | nothing |
| containment | a frame node of two table inputs handing out a table a row whose record is a pair of serials | `attach`, which computes the pairs and keeps one a body |
| link set | a series node handing out a table a row, a record an edge arriving at that row: how many rows back it comes from, the serial there, the serial here, and its measurements. Rows back and not a row number, so a run cut to a window still reads true and `step` needs no more than it is handed | `track`'s `id` column |
| tracklet | a series node reading a link set and handing out a label a record | `track`'s `id`, made with the links and in place of them |
| declared roster, key, hand statements | files on path inputs. A statement's row and place are the footage's | the path input. `resolve`'s labels are rows of a track id |
| assignment set | a series node run whole, handing out a table a row, a record an individual, a serial and a weight | `resolve`'s `identity` column |
| minted roster; a tracklet's or an individual's own measurements; intervals | one table for a run, not one a row | nothing |
| track | a series node handing out a table a row, a record an individual: its place, its kind, the serial it was drawn from | nothing; `kinematics` and `travel` read tracklets |

### 2.3 What the runtime cannot carry, and what changes

**A series node reads one node, and all read one walked node.** A link set that
is a value of its own has to be read beside the observations it joins; an
assignment producer reads links, the observations' evidence and a containment.
What changes: a series tool declares inputs as a frame tool does, each handed to
`run` and each one's row to `step`; a chain node is stepped where all it reads
is; and a walk stacks every frame node a head reads. It reaches `plan.plan`'s
building of the chain and of what is walked, `plan._standing`, `walk._Walk`'s one
stack and its `step`, `walk.run_chain`, `graph.Series` and what `graph.gated`
feeds, `document`'s reading of a series node's inputs, and the oracle of
`tests/stepping.py`. `held.py` keeps a run as node to result and was not read
for more. A tool of one input is the case of one and its documents plan as they
did, which `--plan` over the documents shows before and after. Not sized in
lines.

**A result is a value a row.** A minted roster, what a tracklet is over its whole
length, a bout found by an analysis: each is one table of a run. What changes: a
wire type that is a table of the run, fed whole to what reads it, with no band
and no trace. `held.rows_of` cannot cut one to a window, so a window served from
a longer run is handed the run's table with the run's first row and length, which
`held.Run` already keeps. `csv` writes it. Smaller than the first change and
independent of it.

**A frame node cannot read a series node.** So nothing made from links can go
back to the pixels: a second pass that cuts a blob in two because two tracklets
entered it, a patch of every observation of one tracklet for an appearance model,
a mask painted from tracks to gate an image tool, the occupancy map
`docs/spec/blob-tools.md` holds for want of a kind. What changes is the largest of
the three: a frame node's value at a row would depend on a run, so its key takes
the run's range, the walk makes the series result before the frame nodes that
read it, and the memo's by-row promise gains a second term. Nothing in Part 3
needs it. Without it those producers are absent and the model is not smaller for
it; the route with no change is a table written by one document and read by
another through a path input.

**Names made inside a run.** No change, a rule the encoding keeps: a tracklet's
label and a minted individual are good within the run that made them, as
`track`'s docstring says of its ids, and leave the player only with the run's
first row and length beside them, which `csv`'s name and key line carry. A
declared individual is the same in every run. A reference to an observation is
good against the node key it was made under; a series result says its own key
(`walk.run_chain`) and would say beside it the key of each set it refers into.
For a frame node's table, a containment, the dtype is the one place to say it,
and `docs/findings/2026-11-17-what-keeps-a-dtypes-metadata.md` is why that place
is not to be trusted with it.

**Costs that are not limits.** A node run whole runs at every cadence row of a
walk under way, and an assignment over a long clip is such a node; a tool cannot
say it is worth running only when its walk rests. A span's solve needs the span's
whole graph in the walk, under `walk.STACK_BYTES`; the tracklet's table is what
makes that graph small, and what it weighs on real footage is not measured. Each
chain node hands on the whole table with a column added, where a link set of
edges hands on none of it; whether that is the size `docs/spec/todo.md` asks
after is not measured either.

### 2.4 Carryings turned down

Everything on the one table: links as a list-valued column of each record's
incoming edges, assignments as a list of individuals, contained marks as a list.
It needs no change to the runtime and holds the meeting, the parting, the shared
blob and the candidate set. It cannot hold links between two sets, or anything
back to the pixels, and it forces every series tool into one line: a tool that
reads tracklet speeds and a tool that reads identities must sit one under the
other, and a knob turned on the upper rekeys and reruns the lower, which reads
none of its columns. `docs/spec/a-key-of-what-the-run-reads.md` is the tree's own
argument against a key that holds what the run does not read. Part 5 lays it out
as the choice of no change.

More fields in a series result, handed down the chain: the same one line, with
tables in place of lists.

## Part 3. What survives

| Tool | Under the model | Verdict | Why |
|---|---|---|---|
| `blobs`, `detect` | producers of an observation set | fit with a change | A record wants a serial. `blobs`' `split` cuts an oversized region and "drops it if none does": the model keeps that region as an observation whose count is over one, and a piece wants a containment to what it was cut from |
| `filter` | a new observation set from an old | fits once serials exist | It keeps columns as they are; the serial is one more |
| `sample`, `decode` | measurements | fit | A column a record, NaN where there is none. A code is a marker value and not yet an individual, which is the key's to say |
| `attach` | containment, collapsed | fits with a change | It finds every mark on every body and keeps the largest and a count. The shared blob with two tags in it is the case the model is for, and it keeps one |
| `track` | a link set's producer, of a history's reach | fits with a change to what it hands out | The greedy linker stands. Its output is a label, which has no meeting and no parting; with `merge_ratio` it ends tracklets at a contact and throws away which went into which, and `resolve.contacts` then guesses it back from last centroids and first boxes |
| `tracks-filter` | a new set, chosen by a tracklet's measurements | fits once serials exist | Its `properties` are a table of the run that nothing can be handed |
| `kinematics`, `travel`, `transitions` | measurements and counts along tracklets | fit | They read a label and need no individual. Over a shared observation the motion is the group's, which a count column lets them say |
| `count`, `size`, `spacing` | analyses of an observation set | fit | They need no link. `spacing` counts blobs, so a pair in contact is one; the count column mends that |
| `resolve` | an assignment producer | does not fit; its rules survive | Reads agreeing, exclusion in time and elimination through a contact are the first assignment producer. As it stands an identity is one number a tracklet, so a shared tracklet has none and a candidate set nowhere to go; the number is the marker's own, with no key and no roster; contacts are guessed, as above; and its labels name a track id that `track` assigns "afresh each run", so a label is void when a threshold moves |
| `csv` | the way out of the player | fits with a change | It writes a signal, blobs or tracks, and wants the new kinds of table |
| `region` | the cut in space | outside this | Its piece's record is what places a table on the footage |

What makes a mask, everything above the observation set, is not this
document's.

## Part 4. Beside the earlier attempt

`docs/spec/records-links-tracklets.md` on the branch `tracking-rework-spec`, read
once and after Parts 1 to 3 were written; nothing above was changed for it.

It starts from "The runtime decides the shape" and has as a non-goal any change
to `sieve_player`, so it is the carrying 2.4 turns down, worked out: a record's
name, links as columns of the record's table, every tool in one line. The two
agree that a record wants a name that outlives a filter, that a contact is
recorded once and not guessed twice, and that a label should name a row and a
point. Its own table of what stands in the way names the limits 2.3 names, one
walked node, one input, no reading across a cut, and leaves each as the
runtime's; here each is a change with what it reaches.

Where the model differs. It groups: a tracklet, an individual, a pair counted as
one and an identity are each a column that puts a record in one group. A record
then holds one animal a column, so the shared blob has two individuals nowhere
to go, and a candidate set and a weight likewise; here identity is a relation of
many to many and the count is a measurement. Its links join a row to the rows
before and after with one writer to a table; here an edge may pass over rows,
carries a flow and a cost, and a set of them is one of several over the same
observations, a candidate graph among them. It has no individual apart from a
group, so no roster, no key, and no kind on a track's value.

What it has that this lacks, and that stands under this model as it is. A
record's footprint said as runs, a polygon or none, where 1.3 says only that an
extent is as fine as its producer made it. And a link written by a frame tool
from the overlap of footprints in neighbouring rows, "the same whichever row was
asked for first": in 1.4's words a link set of a frame's reach, which is of no
span, so that for such links the question of a bout walked alone does not arise.
Part 5's one-off is then about `track`, whose reach is a history's.

## Part 5. Kendrick's

**Whether the runtime changes, and how far.** Three sizes. None: the carrying of
2.4, every relation a list on the one table and every series tool in one line.
The first two changes of 2.3: several inputs to a series node with several nodes
walked, and a table of a run. All three: those and a frame node reading a series
node. Recommended: the first two, the table of a run first since it is the
smaller and stands alone; the third when a tool that needs it is wanted, and not
before. The case against none is not that it cannot hold the ants touching, which
it can, but that the tools not yet thought of are the ones that read two things
made apart, and it has no place for them.

**Before or after the pieces of footage.** Recommended: `A piece's record` and `A
table written is in the footage's own pixels and rows` first, since they assume
nothing and a hand statement anchored to the footage has no meaning below a
`region` without them. Then Part 1, accepted or not. Then the question of `A
bout walked alone`, on which the model has a reading and no vote: a result of a
history's or a span's reach is of its span, so the piece walked alone is the
result, and the same rows cut from a longer walk are another result that may
equal it. With links as edges named by rows back the two can be laid side by
side, which ids assigned afresh never could; a one-off over the crossings clip
counting the edges that differ between a window's walk and the clip's says how
far apart the answers are before one is chosen. `period` and `Every piece` after
that. The first change of 2.3 and `A tool that cuts in time` both reach into
`plan.py` and `walk.py`, the second by an amount that spec says is not sized, so
the two are built one after the other and not at once. `Identity across pieces`,
which that spec leaves out, is here a roster's reach and nothing more.

**Every name.** Observation, serial, measurement, link, containment, tracklet,
individual, roster, key, assignment, track, hand statement, and each column.
`track` in Part 1 is a value an individual has and in the tree a tool and a wire
type that carry tracklets; one of the two wants another word. `key` in Part 1 is
what a marker means and in the tree a node's hash; the same.

**Smaller ones.** Whether NaN is the mark of absence or a mask beside the column
is. Whether `core`'s -1 and `id`'s -1 stay, `docs/spec/identity.md` having a
ticked box that `blobs`' own columns are as they were. Whether a whole-run tool
may say it runs only at rest.
