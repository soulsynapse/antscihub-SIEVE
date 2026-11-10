# Geometry: a drawing utility for the file a region reads, opened from the node it feeds

Written 2026-11-10, from Kendrick's request of that day; no box is ticked. Read with
docs/spec/region.md, which settled the geometry file's shape, that it is drawn outside the player,
and that a region refuses a frame of another shape than its plate; with tools/region.py, whose
`load_geometry` is the live statement of what the file may hold; with tools/file.py, the selector
that finds the file; and with the root README's facet table, where `PATHS` says how a file reaches
a node's params. A crop reads a mask and never a geometry file: the chain that feeds a crop from
drawn shapes is file into region, region into blobs-to-mask, the mask into the crop's `roi`, so the
node the utility serves is the region, and a crop is fed through it.

## Why

region.md built the reader and left the writer as a Non-goal of the player, "a utility of its own,
as color_detector_v2 writes inrange's bounds", and its one open Worth-a-look, the drawn outline
sitting where it was drawn on the crossings clip, waits on that writer: no geometry file can be
made today but by hand. A region with nothing wired into `geometry` already says so in its standing,
"no geometry; wire a file selector into geometry", and that is a dead end while there is nothing
that makes the file. The utility is what turns the standing into an action: the card that says the
node is not fed carries the button that opens the tool that feeds it.

A utility is a program of its own and not a tool or a mode of the player. What it hands back is
the config, not how the config was arrived at, as kendrick-scratch.md puts it: the region reads a
file and never learns that a drawing program exists, so the same file can be written by this
utility, by a script, or by hand, and the player's contract with it is the one region.md already
tested. The utility runs as a separate process launched by the node's button, which passes it the
video, the file and the document's folder on its command line, so it imports nothing of
`sieve_player` or `tools`, and a crash or a long drawing session in it costs the player nothing.
Fiji's ROI Manager, napari's shapes layer and the CVAT and LabelMe annotators are the drawing
vocabulary copied here: a shape is drawn by kind, edited by handles, listed by name in a table
beside the image, and saved as a file another program reads; none of those programs is the
consumer of its own ROI file, which is the arrangement this spec keeps.

Three earlier drawing tools of Kendrick's are the evidence for the gestures. antscihub-mask-and-count's
box editor (mask_and_count/box_editor.py) draws a rotated square by two clicks on opposite corners,
the diagonal setting side and angle in one gesture, lists centre, side and angle in an editable
table, and decodes forward rather than seeking inside an .MTS file's first group of pictures,
where OpenCV's seek misses. SIEVE v2's crop tools (src/sieve/gui/video_view.py) drew axis-aligned
rects with eight handles shown on the selection alone, stamped the selected replicate's size, slid
a stamp or a move against the frame's edge rather than trimming it, and recorded in docs/SETTLED.md
that the drawing mode wants one owner or its buttons go stale and that a number field committing
only on Enter keeps shortcuts from firing mid-typing. The optical-flow detector's replicate tab
derived the stamp's size from the selected box after a stored stamp size drifted from it. None of
the three drew a circle or a polygon, and the geometry files under video-tests/ were written by
hand (4203efbc), so nothing is reused as code.

The shapes a user will reasonably want reduce to the two primitives the file holds. A circle is a
dish or a round arena. A square, a rectangle and any polygon, rotated or not, are polygons, since a
rotated rect is four vertices and region.md's fill treats every polygon alike. What the primitives
lose is the editing intent: a square written as four vertices no longer says it should stay square
when resized, and six dishes stamped from one template no longer say they are one template. That
intent is the utility's and is kept in a session file of its own beside the geometry file, never
in the file the region reads.

Which file a region reads for which video is the selector's rule, and the rule as it stands cannot
say "the file named for this video". A file node's `folder` and `pattern` are fixed strings, so one
file for every video is expressible today and one file per video is not: the second needs the rule
to name the video the document has open. That is the one place this spec reaches into the player,
and it is a token in the rule rather than a new kind of selector, as Houdini's `$HIPNAME` and
`$OS` are expanded inside a path parameter and not by a node of their own.

## How to read this

Each `##` below is a deliverable: an `Assumes:` line naming what it builds on, a sentence of why,
then done-when assertions, each a box with a `Check:` that is a test in `tests/`. A box is ticked
by a session once its test passes in the tree; a session never unticks or rewrites an assertion,
and before building toward an unticked box checks whether the tree already meets it. Where a
result is worth Kendrick's eye before the next deliverable leans on it, a `Worth a look:` line says
what to look at; it is not a gate. Nothing here says how. Any deliverable whose `Assumes:` are all
done is available; among those the earlier one in the file first. The branch is done when every
box is ticked.

Words. A *utility* is a program under `utilities/`, one subfolder each, that writes a file a tool
reads through a path input. The *geometry file* and the *plate* are region.md's. A *shape* in the
utility is one of its four *kinds*, circle, square, rectangle and polygon; it is written to the
geometry file as region.md's circle or polygon. The *session* is the utility's own file beside the
geometry file, holding each shape's kind and its stamp group. A *stamp* is a copy of a template
shape placed by a click, identical in kind, size and rotation. The *rule* is a file node's folder
and pattern.

## The utilities folder

Assumes: nothing.

A utility stands alone, so its seam is the same as a tool's in the other direction: tools never
import one another, and a utility imports neither the player nor a tool, which is what lets it be
run, copied or replaced without the player.

Facts to weigh, read off the tree at e17fe0fc. `sieve_player.registry.discover` imports every `.py`
under the roots it is given, `tools/` by default, so a folder beside `tools/` is never scanned for
tools and needs no marker to stay out. tests/test_seams.py reads imports by walking the AST, which
extends to a second folder unchanged. The player's look lives in sieve_player/theme.py; a utility
that may not import it carries its own few colours and its own font choice, and a later change to
the theme does not reach it, which is the price of the seam.

- [ ] `utilities/` holds one subfolder per utility, each runnable as `python -m utilities.<name>`,
  with a README of a few lines saying what file it writes and which tool reads it; nothing under
  `utilities/` imports `sieve_player` or `tools`.
  Check: tests/test_seams.py walks every `.py` under `utilities/` and reads no import of either.

## Opening a video and moving through it

Assumes: The utilities folder.

Shapes are drawn on the frame the region will be wired against, so the utility opens the video the
document has open, at its native size, which is the plate a region compares itself to.

Facts to weigh. The video node hands out the decoded frame at its native size since document
format 2 moved scale onto a rescale node, so the plate is the video's width and height. The
player's Decoder refuses a raw elementary stream for want of an index (docs/spec/sources.md); the
utility reads through OpenCV alone, where a seek in such a stream lands near rather than on the
asked frame, which costs drawing nothing, since the arena does not move between neighbouring frames;
inside an .MTS file's first group of pictures the seek misses badly enough that mask-and-count
decodes forward there instead.

- [ ] Launched with `--video PATH`, the utility shows the video's first frame; with no video it
  asks for one, and the plate is the frame's height and width either way. A seek bar across the
  bottom moves to any frame, with the frame's index and time beside it.
  Check: an offscreen test opens a short clip, reads the plate as the clip's shape, seeks to the
  last frame and reads its index.
- [ ] Ctrl and the wheel zoom about the cursor; zooming out stops at the whole frame fitting the
  view, and zooming in has no practical floor. A Fit button fits the whole frame and a 100% button
  shows one frame pixel to one screen pixel; the view pans by dragging with the middle button or
  with space held. The cursor's position in plate pixels is shown.
  Check: an offscreen test zooms out past fit and reads the scale equal to fit's, presses 100%
  and reads a scale of 1.

## Drawing and editing shapes

Assumes: Opening a video and moving through it.

The four kinds are the ones a user reaches for, and each edits the way it was drawn, so a square
resized stays a square and a circle grows from its rim.

Facts to weigh. tools/region.py's `load_geometry` refuses a shape whose extent passes the plate's
edge, a circle by its bounding box, so a dish drawn at the frame's edge is refused by the region
and not clipped; the utility says so before the region does. A rotated circle is the same circle,
so a circle has no rotation handle.

- [ ] A circle is drawn from its centre by dragging out its radius, and edited by a dot on its rim
  that sets the radius and by dragging its body to move it. A square is drawn by two clicks on
  opposite corners, the diagonal setting its side and angle, as mask-and-count's is; a rectangle
  by two points corner to corner, upright. Each has corner and edge handles to resize, shown on
  the selected shape alone, a square keeping its sides equal under every handle, a handle above it
  to rotate it about its centre, and its body to move it. The drawing mode is one state, shown in
  one place. A polygon is drawn by clicking its vertices and closed by clicking the first again or by
  Enter; each vertex drags, a click on an edge adds a vertex, and a vertex is removed while the
  polygon keeps three; it moves and rotates as the rects do.
  Check: a test of the shapes alone, no window, resizes a square by a corner and by an edge and
  reads its sides equal, rotates a rectangle a quarter turn and reads its vertices, drags a
  circle's rim dot and reads the radius, and adds and removes a polygon's vertex.
- [ ] A shape past the plate's edge is marked as such where it is drawn and in its table row, and
  a save with one refuses and names it, the reason region.md's loader would give.
  Check: a test places a circle reaching past the plate's edge and reads the save's refusal naming it.

## The table, names and deletion

Assumes: Drawing and editing shapes.

The table on the right is the list of what the file will hold, the place a name is typed and the
selection's second handle, as Fiji's ROI Manager is beside its image.

Facts to weigh. A geometry file refuses two shapes of one name and a name that is not a non-empty
string, and region's `choice` and inside's `region_name` column, under its default prefix, carry the name downstream, so a
name is what the user later reads in a csv. Order in the file is what region's `pick` reads last
first and draw paints in order.

- [ ] The table lists every shape, one row each, with its name, its kind and its centre and size in
  plate pixels; selecting a row selects the shape and selecting a shape selects its row; a name is
  edited in place, and a name already taken is refused with the row marked. Delete removes the
  selected shapes.
  Check: an offscreen test draws two shapes, selects the second's row and reads it selected on the
  frame, renames it to the first's name and reads the refusal, and deletes it and reads one row.
- [ ] A new shape is named by a stem and the next free index, the stem a field above the table and
  by default the kind, so six dishes drawn after typing `dish` are dish-1 to dish-6 without a
  keystroke each.
  Check: a test sets the stem, draws three shapes and reads their names; deletes the second, draws
  one and reads the free index taken.

## Stamping and saved shapes

Assumes: The table, names and deletion.

Identical arenas on one plate, six dishes or a well plate, want one shape placed many times, and a
shape drawn once well is worth keeping beyond the session that drew it.

Facts to weigh. A stamp group is editing intent the geometry file cannot hold, so it lives in the
session. The stamp's size is read off the template each time it is placed and never stored
apart from it, the optical-flow detector's drift. A stamp placed near the plate's edge slides
inside it, as v2's did, rather than being refused at save. Kendrick's request names "save a given ROI" beside the stamp; this spec reads it as
saving a shape as a template, kept in a template file of the utility's that any later session
offers to stamp from, and not as a geometry file of one shape, which the save already makes when
one shape is drawn. That reading is the spec's, and the Open section holds the other.

- [ ] A selected shape becomes the stamp: each click places a copy of its kind, size and rotation
  centred at the click, named by the stem's next index, and the copies are one group; resizing or
  rotating one member, with the group's link on, does the same to every member about its own centre.
  Check: a test stamps a square three times, rotates one with the link on and reads all three
  rotated and each centre where it was placed.
- [ ] A selected shape saves as a named template to the utility's template file, and a later
  session lists the templates and stamps from one.
  Check: a test saves a circle as a template, opens a fresh session over the same template file and
  stamps it, reading the radius.

## Saving and reopening

Assumes: Drawing and editing shapes.

The file written is the one region.md's loader reads, and reopening it gives back what was drawn,
kinds and groups included, so a later edit starts where the last one stopped.

Facts to weigh. tools/region.py refuses a shape carrying a key beyond its name and its primitive,
so the kind and the group cannot ride in the geometry file without changing region's loader and
its ticked box in region.md. The session beside it, named for the geometry file, holds them, with
a digest of the geometry file it was written with; a geometry file edited elsewhere then no longer
matches its session, and the utility rebuilds the shapes from the file alone, a circle as a circle,
a polygon of four right angles as a rectangle or a square, any other as a polygon, every group
dissolved, and says that it did. The player's window watches every file a loader read and re-reads
it on a change (region.md's Open, settled by be59a820), so a save while the player is open shows in
the region with no step between.

- [ ] Save writes the geometry file, plate and shapes, every circle as region.md's circle and every
  other kind as a polygon of its vertices in plate pixels, and the session beside it; Open reads
  both back. Launched with `--file PATH`, the utility opens that file, and a path not yet on disk is
  where the first save lands.
  Check: a test draws one of each kind, saves, reads the file through `tools.region.load_geometry`
  and compares each shape's vertices or circle, then reopens and reads the kinds back.
- [ ] A geometry file with no session, or whose session's digest does not match, opens with the
  shapes rebuilt from the file as the Facts say, and the utility says the kinds were inferred.
  Check: a test writes a geometry file by hand of a circle, a rotated square and a triangle, opens
  it and reads circle, square and polygon.
- [ ] A geometry file whose plate is not the open video's shape opens with a line saying the two
  shapes and saves refused until the shapes are moved to the new plate or the video is changed,
  so a file drawn on one camera's frame is never silently written against another's.
  Check: a test opens a file of a 100×100 plate over a clip of another shape and reads the line and
  the refused save.

## The rule, and a file per video

Assumes: Saving and reopening.

Kendrick names the cases a user will want, one file for many videos and one file per video, and the
utility says the rule for the case chosen in the form a file node takes, so the user pastes it into
the node rather than composing a glob.

Facts to weigh, read off the tree at e17fe0fc. tools/file.py's `select(folder, params)` is handed
the document's folder and the node's params and nothing of the video, and
`sieve_player.document.pick_path` is the one caller the window uses, with `_note_selectors` calling
`select` and `matches` for the card's list. sieve_player/window.py's `_pick_video` runs
`_pick_paths` before `pick_video`, so the path inputs are resolved against the video picked on the
previous pass; a rule that names the video needs the video picked first. A token expanded before
`select` is called keeps the selector's contract unchanged: the file tool never learns a token
exists. `rule_for` in tools/file.py already turns a path into folder and pattern for Browse.

- [ ] The utility offers three scopes and shows the rule for the one chosen as a single line,
  relative to the document's folder passed as `--folder`: one file for every video, a fixed name;
  one file per video, named for the video's stem beside it, `{video}.geometry.json`; and one file
  per folder of videos, a fixed name in the video's folder, `{dir}/geometry.json`. Choosing a scope
  sets where Save writes, and a copy button puts the line on the clipboard.
  Check: a test sets each scope over a clip in a subfolder of the document's and reads the line and
  the save path.
- [ ] A file node's pattern and folder expand `{video}` to the stem of the video the document has
  open and `{dir}` to that video's folder relative to the document, before the rule is asked; a
  document with no video expands neither and the node says so. The video is picked before the path
  inputs are, so a region reads the file named for the video just opened.
  Check: a test builds a document with a file node on the video and a second on a region's
  geometry with the pattern `{video}.geometry.json`, switches the video and reads the region's
  plate change to the second file's.
- [ ] A path pasted into a file node's pattern that carries a folder splits on commit into folder
  and pattern, as Browse's `rule_for` does, so the utility's one line is one paste.
  Check: a test sets the pattern to `geometry/{video}.geometry.json` and reads folder `geometry`
  and pattern `{video}.geometry.json`.

## The region card's button

Assumes: Saving and reopening.

The node that is not fed is where the user is when they learn it, so its card carries the way to
feed it, and the button hands the utility everything the player knows: the video, the file the rule
picked or would pick, and the document's folder.

Facts to weigh, read off the tree at e17fe0fc. sieve_player/pane.py hands every settings widget
with `set_source` the open video's path and fps, which is tools/_csvfile.py's Write widget's way of
knowing the footage, so the video reaches a region's card through an existing seam. No seam hands a
widget the path its selector picked; `_pick_paths` writes it only into the pane's note line as a
basename. A path input that matched nothing has no path, but a rule with no wildcard after its
tokens are expanded names one file, which is where the utility saves. One utility exists, so the
button is region's own, built in its settings widget as csv's Write is, and no facet for "a path
input has a utility" is minted until a second tool wants one, as the Tab menu's presentation waited
on a second (cd7fac9f, on the unmerged v5-naming branch). The process is launched with the interpreter the player runs under and is
not waited on.

- [ ] The window hands a settings widget that asks for it the document's folder and, per path
  input, the path its selector picked or, matching nothing, the one file its rule names, or None.
  Check: an offscreen test wires a file node into a region's geometry with a rule naming a file not
  on disk and reads that path handed to the region's widget.
- [ ] A region's card shows, under its standing, a button that opens the geometry utility with the
  open video, the path its geometry input is handed and the document's folder; with nothing wired
  into `geometry` the button still opens the utility on the video, its scope unset. Saving in the
  utility while the region is wired to that file updates the region's shapes in the open player.
  Check: a test replaces the launch with a recorder, presses the button and reads the command
  line; an offscreen test writes the region's geometry file and reads the region's params follow.

Worth a look: region.md's open one, a geometry file drawn in the utility over the crossings clip
(video-tests/00000_168-178.mp4) around the nest, loaded into a region on the purb document, its
outline on the frame where it was drawn, and a crop fed from it.

## Non-goals

- The utility writing anything but the geometry file, its session and its template file. A mask
  image, a crop rect or a document node is the player's to derive from the file.
- An ellipse, an annulus or a shape with a hole as a kind. The file has circle and polygon;
  region.md settles a hole as one region less another through combine, and an ellipse is a polygon
  the utility does not yet offer to draw.
- Shapes that move over the video. A geometry file is one plate's, the same at every row, as
  region's STATIC says.
- The utility editing the document, placing a file node or wiring it. The rule is pasted.
- A facet for utilities in the registry, until a second tool has one.

## Open

- Whether "save a given ROI" means a template to stamp from, which this spec builds, or a geometry
  file of one shape written beside the full one. Kendrick's reading decides; the second is a save
  of the selection and costs little.
- Whether the button, with nothing wired into `geometry`, places and wires a file node with the
  rule of the scope chosen, so that the paste is unneeded. Held: it is the utility writing the
  document, the Non-goal above, and waits until the paste has been lived with.
- A grid stamp, rows and columns at a pitch, for well plates; whether stamping by clicks is slow
  enough to want it is Kendrick's to say after use.
- A circle through three points on its rim, for an arena whose centre is hidden or whose edge is
  all that is visible; drawing from the centre is the spec's default and this is the common second.
- Drawing over a background rather than one frame, the median of sampled frames, so animals on
  the arena's edge do not hide it. The utility may not import background, so it would carry its
  own median.
- Undo. Every annotator named in the Why has it, and v2's took one drag as one step; it is not a
  box because nothing here is destructive past Delete, and Delete's loss is one shape.
- Whether "a two point square" means mask-and-count's diagonal, which sets the angle in the same
  gesture and is what this spec builds, or an upright square from two corners, rotated after.
- A scale, pixels per millimetre from a drawn length, carried in the geometry file for exports in
  physical units, as the optical-flow detector's calibration dialog drew one. Region's loader refuses an unknown key on a shape but passes one at the top
  level, unstated in its docstring; whether that tolerance is a contract is decided with the next
  item, and the scale waits on the first export that asks.
- The session as its own file or as a top-level key of the geometry file. The loader's tolerance
  of a top-level key would let the kinds and groups ride in the one file, with no second file to
  lose and no change to region; it puts how the config was arrived at into the config, against
  kendrick-scratch.md's line, and makes a tolerance nobody declared into a contract. The spec
  builds the separate file; Kendrick's reading of the scratch line decides.
