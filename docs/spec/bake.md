# Bake: a node that writes what it receives to a store and reads it back while the stamp holds

Written 2026-11-07; the ticked boxes below are what the tree has. Read with the registry's type report
(`python -m sieve_player.registry`), the live statement of what feeds what, and with the facet table
in the root README. docs/spec/sources.md is the plan this one supersedes in part: its crop clips are
the first bakes, and what it keeps, many rects of one plate under one pipeline, waits on the
processing-run branch and is not here.

## Why

The chain between the video node and the first measurement, rescale, gray, a crop once there is one, is where the time
and the bytes go, and nothing after it can change that: the decode is paid in full whatever is
cropped or scaled afterwards, since the codec has no partial decode, and a 600-row window either
fits the decoder cache or serves a rewalk nothing (docs/findings/2026-10-31-window-fit-and-lru-thrash.md).
The player's answer so far was to fold the settled transforms into the video node, `scale` applied
before the decoder's cache, which buys the footprint and not the decode, and grows a hidden pipeline
inside one node, knob by knob, in the shape of Blender's VSE proxies. The alternative every DCC
settled on is the one node that freezes its input to disk, Houdini's File Cache SOP and Blender's
Geometry Nodes Bake node: placed on any wire, passing its input through until baked, then reading
the file while a stamp says it is still the file this graph would produce. It knows nothing about
what is upstream, so it never needs a per-tool roll-up, and the one thing it buys that no setting
can is the smaller file: after it, the decode is the small frame's.

What it writes is decided by the kind flowing into it, a frame kind to a clip the video node can
open, a table kind to a table file, a signal to a csv, so the writer scales with the kinds, of
which there are few, and not with tools times knobs. docs/findings/2026-11-04-remux-encode-and-seek.md
measured what the frame writer costs and what the written file then costs to read.

## How to read this

Each `##` below is a deliverable: an `Assumes:` line naming what it builds on, a sentence of why,
then done-when assertions, each a box with a `Check:` that is a test in `tests/`. A box is ticked
by a session once its test passes in the tree; a session never unticks or rewrites an assertion,
and before building toward an unticked box checks whether the tree already meets it. Where a
result is worth Kendrick's eye before the next deliverable leans on it, a `Worth a look:` line says
what to look at; it is not a gate. Nothing here says how. Any deliverable whose `Assumes:` are all
done is available; among those the earlier one in the file first. The branch is done when every
box is ticked.

## The video node hands out frames as decoded

Assumes: nothing.

`scale` on the video node is tools/rescale.py's resize run inside the decoder, kept there for the
cache footprint. With a bake to carry the footprint it is a second place a transform can live, and
the rule that keeps the video node from growing again is that a param of its is legitimate only
where it changes the decoder's work, which `output` does and a resize does not.

- [ ] The video node's params are `output` alone; the decoder has no scale, and the video node's key
  hashes the path and the output.
  Check: a test reads the video node's settings and the plan's base key with no scale in either.
- [ ] A saved document whose video node carries a scale loads with a rescale node of that factor
  between the video node and every node that read it, so what reaches each reader is the plane it
  read before; the tuned documents under video-tests/ are such documents.
  Check: a test loads a document with a scaled video node and reads the inserted node and its
  readers' frames.
- [ ] README's bullet on the video node's params and every docstring that said the scale was the
  decoder's say what is now true.
  Check: `tests/test_seams.py` green and a grep for the old claim finding nothing.

## The store

Assumes: nothing.

A baked clip of a long session is gigabytes and belongs on whatever disk has them, not beside the
document. One folder the user chooses, remembered across launches, default beside the log under the
local app data folder (`sieve_player.dev.console.log_path` is the precedent for where), is the
store, and a bake lands in it under its key, so two documents with the same chain share a bake and
a rebake under a new key sits beside the old one rather than over it. The key hashes the video's
resolved path with everything upstream, so a moved file is a new key and two machines never
collide, and sharing by key is settled rather than open. What the key does not hash is a tool's
code, so the sidecar records the repository commit the bake was written under, for a later check
to read.

- [ ] A module says where the store is: the folder chosen, else `SIEVE_STORE` from the launch
  environment, else the default; the choice survives a relaunch.
  Check: a test resolves each of the three and reads a choice back through a fresh call.
- [ ] A file in the store is named by the node's key, with a sidecar beside it saying the key, the
  kind, the document and node it came from, the rows and increment baked, the source's fps and the
  written one, the plane shape, the quality, the repository commit and the time written; a sidecar
  is what makes the file ours.
  Check: a test writes a bake and reads every field back off the sidecar.
- [ ] The player shows the store's folder, how much it holds and how much the disk has free, and
  lets the user change the folder; a folder that cannot be written is refused with the reason.
  Check: a test on the function the display reads, with an unwritable folder.

## A bake node, live

Assumes: nothing.

Placed on a wire of any kind the graph has, it is the identity until baked, so the chain tunes
exactly as it did without it. Whether one tool serves frame and series kinds or two share a
module is the builder's call; the user places one thing called bake.

- [ ] A bake node accepts every type the registry's report lists and produces the same; wired on a
  frame kind its reader gets the frame, on a table kind the table, on a signal the signal, and the
  node's standing says live.
  Check: a test places one on a gray wire, a blobs wire and a signal wire and reads each reader's
  input against the chain without it.
- [ ] The node's params are the rows to bake, from and to with blank meaning the clip's ends, the
  increment, one row in every so many, and the frame writer's quality, two positions, lossless and
  standard, never a continuous rate; none of them changes what a live node hands out.
  Check: a test changes each and reads the live output unchanged.

## Baking

Assumes: The store, A bake node, live.

The action writes the node's input over the whole range, which is the first whole-clip pass in the
player that produces something; it runs where the clip walk runs, off the GUI thread, with
progress on the node and a cancel, and a run that does not finish leaves nothing, as every writer
in tools/ already promises. The increment is where time decimation lives: dropping rows is not a
thing a frame tool can do, one row in and one out, so tools/downsample.py's hold-every-N preview was
the sign it belonged here.

- [ ] Bake on the node writes its input from the first row to the last of the range, every increment
  rows, into the store under the node's key with its sidecar, on the worker, with progress said on
  the node; when it is done the node is baked.
  Check: a test bakes a short chain over a synthetic clip and finds the file, the sidecar and the
  node's mode.
- [ ] Cancel, a tool raising mid-bake, or the store refusing a write leaves no file and no part of
  one, and the node stays live with the reason in its standing.
  Check: a test cancels one bake and fails another and reads the store and the standing.
- [ ] A frame kind writes a clip the video node opens: gray and bgr at the node's quality, a mask
  losslessly; the clip's row count is the rows baked and its fps the source's over the increment.
  Check: a test bakes each of the three, opens the clip through the decoder and reads count, fps,
  the mask equal and the gray within the quality's tolerance.
- [ ] A baked gray clip is in a pixel format the decoder reads through its luma path
  (docs/findings/2026-11-01-luma-read.md), so a row of the bake never pays the conversion the chain
  it replaced had already shed.
  Check: a test opens a baked gray clip and reads the decoder's luma-read flag.
- [ ] A table kind reads back equal, every column and its dtype, `contour` included; a signal reads
  back equal.
  Check: a test bakes blobs, tracks and a signal and compares.

Worth a look: whether standard is distinguishable from lossless on the blobs table, which is
sources.md's first open item as a finding: one chain over the live frames and over each bake,
tables diffed. The luma finding already accepted an error of this class without retuning, so the
expectation is that it is not, and standard is the default once the finding says so; until then
the default is the builder's and the sidecar records which was used.

## Reading back

Assumes: Baking.

Baked, the node is a source: its readers' rows come from the file, nothing upstream of it runs, and
the plate is not decoded, which is the whole gain. A change upstream does not silently throw that
away, since a baked node is how two settings of the upstream are compared and how a long run stays
cheap while the operator keeps tuning; it marks the node stale and the user chooses between
rebaking and going live, as Houdini's load-from-disk toggle does. While baked, the node's key is the
file's, so what is downstream is keyed on what it actually receives.

- [ ] In baked mode a scrub and a walk decode no row of the video and run no node upstream of the
  bake; the readers' rows are the file's.
  Check: a test scrubs a baked graph and counts decodes and runs through the probe.
- [ ] A change upstream of a baked node leaves it serving the file, with stale in its standing, and
  the node's key, hence every key downstream, unchanged; switching the node to live serves the
  chain and takes the live key; baking again writes under the new key beside the old file.
  Check: a test changes an upstream knob, reads the standing and the sync keys, switches, and bakes.
- [ ] A document reopened finds the bake under its node's key in the store and opens baked; a
  document whose bake is gone from the store opens live and says so.
  Check: a test saves, reopens, and reopens again with the file removed.
- [ ] A baked frame clip is a file another document opens as its video, at the baked fps and shape,
  which is sources.md's crop as a source.
  Check: a test opens a baked clip as a new document's video and reads its facts.

Worth a look: the window fit on the crossings clip with rescale live, then baked, read off the
monitor's store lanes, since that is the claim this spec rests on and the one figure that says
whether the branch did what it was for. It belongs in a finding beside the window-fit one.

## Downsample retired

Assumes: Baking.

tools/downsample.py's scale is rescale's and its every-N is the increment, and its export is the
per-tool roll-up below. It is the only tool declaring `output_name`, `export_command` and
`describe_output`, and the registry's check fails only on a facet the player does not read, so the
tool, the pane's export block and the three facets go together or not at all.

- [ ] tools/downsample.py is gone, with the export block and the three facets, and the registry's
  check and the facet table in README agree.
  Check: `python -m sieve_player.registry --check` green and a test that the registry's FACETS
  names none of the three.

## Non-goals

- Many rects of one plate under one pipeline, with one decode serving every rect: sources.md's
  wedge, which is a run over parameter sets and belongs to the processing-run branch; a bake node
  knows nothing about N.
- The processing run itself. Baking is one whole-clip pass with one consumer, the writer; the run
  that executes every bake and output of a document over a clip generalizes it later and may change
  how the pass is driven, not what a bake is.
- Rebaking on its own when the upstream changes. Stale is shown, never acted on.
- A store browser or collection. The store is a folder of files named by key with sidecars naming
  their document and node; the user deletes in it with the file manager, and the player says what
  it holds and what is free.
- A crop tool, and with it how a table found in a cropped plane is placed back on the plate. Crop
  is the transform the bake is for, and it lands as its own tool when it is wanted; the bake needs
  nothing from it.
- Baking a flow field. Eight bytes a pixel with no consumer that wants it from disk; when one
  exists the writer is a kind, not a change to the node.
- Per-tool roll-ups, tools/downsample.py's ffmpeg filter path included: bake writes what it
  receives, and the one ffmpeg it runs encodes frames handed to it.

## Open

- Acting on a bake whose sidecar's commit is older than a change to a tool upstream of it. The
  sidecar carries the commit from the first bake written; whether that becomes a second kind of
  stale, shown on the node, waits on the first time a bake is served fresh after a tool changed.
