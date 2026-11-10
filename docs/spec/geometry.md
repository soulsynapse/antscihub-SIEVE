# Geometry: a drawing utility for the file a region reads, opened from the node it feeds

Written 2026-11-10, from Kendrick's request of that day and his reading of the first draft the same
day; no box was ticked then. Amended the same day after an architect review ran its Facts against the tree
at 9f3ea91a and its deliverables against one another: the card's button reaches the wired file by
its path, which the window hands the card, where it had matched the region's shapes against files
on disk and a configuration kept in the library made two matches of every file saved from it; a
shape past the plate is never written, and is held only as the marked shape of a file opened over
another plate; the launch is checked from a working directory that is not the repo's root; the
table reorders, file order being what a click in the player reads; and the plate is checked against
the player's Decoder. Read with docs/spec/region.md, which settled the geometry file's shape, that
it is drawn outside the player, and that a region refuses a frame of another shape than its plate;
with tools/region.py, whose `load_geometry` is the live statement of what the file may hold; with
tools/file.py, the selector that finds the file; and with the root README's facet table, where
`PATHS` says how a file reaches a node's params. A crop reads a mask and never a geometry file: the
chain that feeds a crop from drawn shapes is file into region, region into blobs-to-mask, the mask
into the crop's `roi`, so the node the utility serves is the region, and a crop is fed through it.
The one change to `sieve_player` is the window handing a card the file each of its path inputs
picked; the rest is a new folder, a button on region's card and a line of region's contract.

## Why

region.md built the reader and left the writer as a Non-goal of the player, "a utility of its own,
as color_detector_v2 writes inrange's bounds", and its one open Worth-a-look, the drawn outline
sitting where it was drawn on the crossings clip, waits on that writer: no geometry file can be
made today but by hand. A region with nothing wired into `geometry` already says so in its standing,
"no geometry; wire a file selector into geometry", and that is a dead end while there is nothing
that makes the file. The utility is what turns the standing into an action: the card that says the
node is not fed carries the button that opens the tool that feeds it.

A utility is a program of its own and not a tool or a mode of the player. Region's loader reads a
file and never learns that a drawing program exists, so the same file can be written by this
utility, by a script, or by hand, and the player's contract with it is the one region.md already
tested; region's card alone names the utility, by its module and its command line. The
utility runs as a separate process launched by the node's button, which passes it what the card
knows on its command line, so it imports nothing of `sieve_player` or `tools`, and a crash or a long
drawing session in it costs the player nothing. Fiji's ROI Manager, napari's shapes layer and the
CVAT and LabelMe annotators are the drawing vocabulary copied here: a shape is drawn by kind, edited
by handles, listed by name in a table beside the image, and saved as a file another program reads.

Three earlier drawing tools of Kendrick's are the evidence for the gestures. antscihub-mask-and-count's
box editor (mask_and_count/box_editor.py) draws a rotated square by two clicks on opposite corners,
the diagonal setting side and angle in one gesture, lists centre, side and angle in an editable
table, and decodes forward rather than seeking inside an .MTS file's first group of pictures,
where OpenCV's seek misses. SIEVE v2's crop tools (src/sieve/gui/video_view.py) drew axis-aligned
rects with eight handles shown on the selection alone, stamped the selected replicate's size, slid
a stamp or a move against the frame's edge rather than trimming it, took one drag as one undo
step, and recorded in docs/SETTLED.md that the drawing mode wants one owner or its buttons go stale
and that a number field committing only on Enter keeps shortcuts from firing mid-typing. The
optical-flow detector's replicate tab derived the stamp's size from the selected box after a stored
stamp size drifted from it. None of the three drew a circle or a polygon, and the geometry files
under video-tests/ were written by hand (4203efbc), so nothing is reused as code.

The shapes a user will reasonably want reduce to the two primitives the file holds. A circle is a
dish or a round arena. A square, a rectangle and any polygon, rotated or not, are polygons, since a
rotated rect is four vertices and region.md's fill treats every polygon alike. What the primitives
lose is the editing intent: a square written as four vertices no longer says it should stay square
when resized, and six dishes stamped from one template no longer say they are one group. That
intent rides in the same file under a key of its own, which the region ignores; one file is the
thing a user copies, moves and wires, and a second beside it is one more thing to lose. Decided
2026-11-10.

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
geometry file as region.md's circle or polygon. The *drawing* is the top-level key of the geometry
file that holds each shape's kind and stamp group, the utility's and never the region's. A *stamp*
is a copy of a shape placed by a click, identical in kind, size and rotation. A *saved
configuration* is a geometry file kept in the utility's own library, which every later run of the
utility lists.

## The utilities folder

Assumes: nothing.

A utility stands alone, so its seam is the same as a tool's in the other direction: tools never
import one another, and a utility imports neither the player nor a tool, which is what lets it be
run, copied or replaced without the player.

Facts to weigh, read off the tree at e17fe0fc. `sieve_player.registry.discover` imports every `.py`
under the roots it is given, `tools/` by default, so a folder beside `tools/` is never scanned for
tools and needs no marker to stay out. tests/test_seams.py reads imports by walking the AST; its
`imports_of` is bound to `sieve_player`'s own modules, so the utilities' check is a walk of its own,
as the tools' is. pyproject.toml packages `sieve_player` alone and main.py finds `tools` through its
own folder, so `utilities` is importable only with the repo's root on the path, and a process
started by module name resolves it against its own working directory, not the player's script. The
player's look lives in sieve_player/theme.py; a utility that may not import it carries its own few
colours and its own font choice, and a later change to the theme does not reach it, which is the
price of the seam.

- [x] `utilities/` holds one subfolder per utility, each runnable as `python -m utilities.<name>`
  from the repo's root, with a README of a few lines saying what file it writes and which tool
  reads it; nothing under `utilities/` imports `sieve_player` or `tools`.
  Check: tests/test_seams.py walks every `.py` under `utilities/` and reads no import of either.

## Region's file holds the drawing

Assumes: nothing.

The one file carries the drawing beside the plate and the shapes, so the region's tolerance of a
key it does not read becomes its stated contract rather than an accident a later tightening of the
loader would undo.

Facts to weigh, read off the tree at e17fe0fc. `load_geometry` checks that `plate` and `shapes`
are present and reads nothing else at the top level, so a further key already passes; its
docstring does not say so. It refuses a shape carrying any key beyond its name and its primitive,
which is why the drawing is a top-level key and not one on each shape. The loader answers only
`plate` and `shapes` as params, so the drawing never reaches the node's params or its key, and
editing a shape's kind without moving it re-keys nothing.

- [x] region's module docstring says a geometry file's top-level keys other than `plate` and
  `shapes` are ignored, and the loader's answer is the same with them as without.
  Check: a test loads a file with a further top-level key and reads params equal to the file's
  without it.

## Opening a video and moving through it

Assumes: The utilities folder.

Shapes are drawn on the frame the region will be wired against, so the utility opens the video the
document has open, at its native size, which is the plate a region compares itself to.

Facts to weigh. The video node hands out the decoded frame at its native size since document
format 2 moved scale onto a rescale node, so the plate is the video's width and height. The
player's Decoder refuses a raw elementary stream for want of an index (docs/spec/sources.md); the
utility reads through OpenCV alone, where a seek in such a stream lands near rather than on the
asked frame, which costs drawing nothing, since the arena does not move between neighbouring
frames; inside an .MTS file's first group of pictures the seek misses badly enough that
mask-and-count decodes forward there instead. The player's Decoder opens through OpenCV's FFmpeg
backend by name, and a region refuses a frame of any shape but its plate, so a utility whose
OpenCV picked another backend, or turned a frame the Decoder does not, would write files every
region refuses; the two may not share code, so a test holds them to one answer.

- [x] Launched with `--video PATH`, the utility shows the video's first frame; with no video it
  asks for one, and the plate is the frame's height and width either way, the shape the player's
  Decoder reads for the same file. A seek bar across the bottom moves to any frame, with the
  frame's index and time beside it.
  Check: an offscreen test opens a short clip, reads the plate as the clip's shape and as the
  shape of `sieve_player.decoder.Decoder`'s first frame of it, seeks to the last frame and reads
  its index.
- [x] Ctrl and the wheel zoom about the cursor; zooming out stops at the whole frame fitting the
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
edge, a circle by its bounding box, so a shape off the plate is never written: a move, a resize or
a stamp that would carry a shape past the edge stops it at the edge, as v2's slid, and a drawing
gesture begun inside the plate is held inside it. A rotated circle is the same circle, so a circle
has no rotation handle.

- [ ] A circle is drawn from its centre by dragging out its radius, or through three clicks on its
  rim, and edited by a dot on its rim that sets the radius and by dragging its body to move it. A
  square is drawn by two clicks on opposite corners, the diagonal setting its side and angle, as
  mask-and-count's is; a rectangle by two points corner to corner, upright. Each has corner and
  edge handles to resize, shown on the selected shape alone, a square keeping its sides equal
  under every handle, a handle above it to rotate it about its centre, and its body to move it. A
  polygon is drawn by clicking its vertices and closed by clicking the first again or by Enter;
  each vertex drags, a click on an edge adds a vertex, and a vertex is removed while the polygon
  keeps three; it moves and rotates as the rects do. The drawing mode is one state, shown in one
  place.
  Check: a test of the shapes alone, no window, resizes a square by a corner and by an edge and
  reads its sides equal, rotates a rectangle a quarter turn and reads its vertices, drags a
  circle's rim dot and reads the radius, fits a circle through three points of a known circle and
  reads its centre and radius, and adds and removes a polygon's vertex.
- [ ] No shape within the plate leaves it: a move, a resize, a rotation or a three-point circle that
  would pass the edge stops at it, and every shape the utility writes is one region's loader
  accepts. The one shape held past an edge is a shape of a file opened over another plate, which
  Saving and reopening marks.
  Check: a test drags a circle and a rotated square toward each edge and reads every extent within
  the plate; a test saves after each and loads the file through `tools.region.load_geometry`.
- [ ] Every draw, edit, rename, stamp and delete is one undo step, a drag being one step however
  long; Ctrl+Z undoes and Ctrl+Shift+Z redoes.
  Check: a test draws a square, drags it twice and deletes it, undoes three times and reads the
  square at its first drag's end, and redoes once.

## The table, names and deletion

Assumes: Drawing and editing shapes.

The table on the right is the list of what the file will hold, the place a name is typed and the
selection's second handle, as Fiji's ROI Manager is beside its image.

Facts to weigh. A geometry file refuses two shapes of one name and a name that is not a non-empty
string, and region's `choice` and inside's `region_name` column, under its default prefix, carry
the name downstream, so a name is what the user later reads in a csv. Order in the file is what
region's `pick` reads last first and draw paints in order.

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
- [ ] A row moves up and down the table, one undo step a move, and the file's order is the
  table's, so of two shapes one inside the other the inner is put after the outer and is the one a
  click in the player picks.
  Check: a test draws a small circle and then a large one around it, saves and reads
  `tools.region.pick` at the small one's centre answer the large one's name; moves the small one's
  row below the large one's, saves and reads the small one's.

## Stamping

Assumes: The table, names and deletion.

Identical arenas on one plate, six dishes or a row of nest boxes, want one shape placed many times
and kept identical after.

Facts to weigh. A stamp group is editing intent the shapes cannot hold, so it lives in the
drawing. The stamp's size is read off the selected shape each time it is placed and never stored
apart from it, the optical-flow detector's drift.

- [ ] A selected shape becomes the stamp: each click places a copy of its kind, size and rotation
  centred at the click, held inside the plate, named by the stem's next index, and the copies and
  the original are one group; resizing or rotating one member, with the group's link on, does the
  same to every member about its own centre, a member the change would carry off the plate
  stopping the change for all.
  Check: a test stamps a square three times, rotates one with the link on and reads all four
  rotated and each centre where it was placed.

## Saving and reopening

Assumes: Region's file holds the drawing, Drawing and editing shapes, Stamping.

The file written is the one region's loader reads, and reopening it gives back what was drawn,
kinds and groups included, so a later edit starts where the last one stopped.

Facts to weigh. The drawing names each shape it describes, so a geometry file edited elsewhere can
disagree with it: a shape the drawing does not name, or whose primitive no longer fits the kind the
drawing gives it, is rebuilt from the primitive alone, a circle as a circle, a polygon of four
right angles as a rectangle or a square, any other as a polygon, out of any group, and the utility
says which it inferred. The player's window watches every file a loader read and re-reads it on a
change (region.md's Open, settled by be59a820), so a save over the file a region is wired to shows
in the region with no step between. A file node's `folder` is joined to the document's folder and
an absolute folder survives the join, and its Browse turns a picked file into the rule, so a saved
file reaches a node by Browse or by pasting its folder and its name into the two fields.

- [ ] Save writes the geometry file, plate, shapes and drawing, every circle as region.md's circle
  and every other kind as a polygon of its vertices in plate pixels; Open reads it back with its
  kinds and groups. Launched with `--file PATH`, the utility opens that file, and a path not yet on
  disk is where the first save lands; with neither, the first save asks, beside the video by
  default. The utility shows the saved file's folder and name, each with a copy button, for a file
  node's two fields.
  Check: a test draws one of each kind and a stamp group, saves, reads the file through
  `tools.region.load_geometry` and compares each shape's vertices or circle, then reopens and
  reads the kinds and the group back.
- [ ] A geometry file with no drawing, or one whose drawing disagrees with a shape, opens with that
  shape rebuilt from its primitive as the Facts say, and the utility says the kinds were inferred.
  Check: a test writes a geometry file by hand of a circle, a rotated square and a triangle, opens
  it and reads circle, square and polygon.
- [ ] A geometry file whose plate is not the open video's shape opens with a line saying the two
  shapes, every shape past the new plate's edge marked, and the save refused while any is, so a
  file drawn on one camera's frame is never silently written against another's. A marked shape
  moves and resizes with no edge holding it until it is within the plate, where the mark goes and
  the edge holds it as it does any other.
  Check: a test opens a file of a 200×200 plate holding a shape near its far corner over a
  100×100 clip and reads the line, the marked shape and the refused save; drags the shape within
  the plate and reads the mark gone, the save taken, and a further drag toward the edge stopped at
  it.

## Saved configurations

Assumes: Saving and reopening.

A configuration drawn once, the arena of a rig, is wanted again on the next video and in the next
document, so the utility keeps what it saves where every later run of it can list it, whichever
SIEVE document opened it.

Facts to weigh. A saved configuration is a geometry file like any other, drawing included, so
loading one is opening it and the plate check of the deliverable before covers a configuration
saved on another camera's frame. The library is the utility's and not a document's, so it lives in
one folder per user outside the repo and outside any document's folder, where Qt's per-user
application data location puts it; the README names where.

- [ ] Saving to the library keeps the current configuration under a name the user gives, with the
  plate and the date; the library lists every configuration kept, with those, on every run of the
  utility, and choosing one loads its shapes onto the open video under the plate check. A kept
  configuration is renamed or removed from the list.
  Check: a test saves a configuration to a library folder it names, starts a fresh utility over
  the same folder and another clip of the same shape, reads it listed, loads it and reads the
  shapes; a test loads one kept on another plate and reads the line.

## The window tells a card the file it reads

Assumes: nothing.

A card that opens a program on the file its node reads has to know which file that is, and the
window is the one place that does.

Facts to weigh, read off the tree at 9f3ea91a. `_pick_paths` in sieve_player/window.py holds the
full path each path input's selector picked and writes it only into the pane's note line, as a
basename. A few lines on, the same function tells the node's widget which of its rows a selector
drives, through `set_driven` where the widget has one; `set_source`, `show_matches` and
`show_result` are told the same way, each to a widget that has the method and to no other, and the
root README lists them beside `settings`. The path cannot ride in the loader's answer in place of
a hook: what a loader answers becomes the node's params, sieve_player/plan.py keys a node on its
params, and a geometry file renamed would re-key the region and everything after it.

- [ ] A settings widget with a `set_paths` is handed, each time the window picks the path inputs,
  a dict of input name to the absolute path of the file its selector picked, an input with nothing
  wired or nothing matched absent from it; the root README names the hook beside `set_source`.
  Check: an offscreen test wires a file selector into a path input of a tool whose widget records
  `set_paths`, reads the picked file's path handed under the input's name, breaks the wire and
  reads an empty dict handed.

## The region card's button

Assumes: Saving and reopening, The window tells a card the file it reads.

The node that is not fed is where the user is when they learn it, so its card carries the way to
feed it, and the button hands the utility what the card knows.

Facts to weigh, read off the tree at e17fe0fc. sieve_player/pane.py hands every settings widget
with `set_source` the open video's path and fps, and calls it again whenever the video changes,
which is tools/_csvfile.py's Write widget's way of knowing the footage, so the video reaches a
region's card as it reaches csv's. The file reaches it through `set_paths`, so the button's whole
hand-off is the two paths Saving and reopening already takes, and a save over the file the region
is wired to reaches the region through the watcher. One utility exists, so the button is region's
own, built in its settings widget as csv's Write is, and no facet for "a path input has a utility"
is minted until a second tool wants one. The process is launched with the interpreter the player
runs under and is not waited on; the player's working directory is wherever it was started, so
the launch says where `utilities` is found and never leans on the directory it inherits.

- [ ] A region's card shows, under its standing, a button that opens the geometry utility with
  `--video`, the video `set_source` handed the card, and `--file`, the file `set_paths` handed it
  for `geometry`; with no file handed it opens the utility on the video alone. A save there
  updates the region's shapes in the open player.
  Check: with the working directory elsewhere than the repo's root, a test replaces the launch
  with a recorder, presses the button and reads the video and the file in what was recorded; gives
  the recorded arguments to the utility's own parser and reads the same two back; runs the
  recorded launch for real with `--help` in place of its arguments and reads a clean exit; an
  offscreen test rewrites the region's wired file and reads the region's params follow.

Worth a look: region.md's open one, a geometry file drawn in the utility over the crossings clip
(video-tests/00000_168-178.mp4) around the nest, loaded into a region on the purb document, its
outline on the frame where it was drawn, and a crop fed from it.

## Non-goals

- Any change to `sieve_player` past the one hook, `set_paths`. The video reaches the card through
  `set_source`, and the saved file reaches the region through the watcher the window already has.
  Decided 2026-11-10; the hook admitted the same day, on the architect review.
- One file per video, a rule that names the video the document has open. It is a change to the
  selector's contract, and waits. Decided 2026-11-10.
- A shape off the plate, written, or drawn or moved there. One opened over a smaller plate is held
  marked until it is brought within. Decided 2026-11-10.
- The utility finding the file a region reads by searching for it. The card is told the path and
  hands it on.
- The utility writing anything but geometry files, in place or in its library. A mask image, a crop
  rect or a document node is the player's to derive from the file, and the rule is pasted or
  browsed, never written into the document.
- An ellipse, an annulus or a shape with a hole as a kind. The file has circle and polygon;
  region.md settles a hole as one region less another through combine.
- Shapes that move over the video. A geometry file is one plate's, the same at every row, as
  region's STATIC says.
- A grid stamp, a background to draw over in place of a frame, and a pixels-per-millimetre scale.
  Kendrick's reading of the first draft found none needed. Decided 2026-11-10.
- A facet for utilities in the registry, until a second tool has one.

## Open

- What a stamp group is once its members differ. The link propagates a resize and a rotation, and
  with it off one member is resized alone, so a group is not a promise that its members are
  identical; a polygon member's vertex dragged, added or removed is neither a resize nor a
  rotation, and whether that propagates, is refused under the link, or takes the member out of its
  group is not said, nor what "the same" resize means across members of different sizes. Kendrick's
  to decide before Stamping is built past a group of identical members.
- The first save after a launch with no file handed lands beside the video by default, and a file
  selector's `folder` is read against the document's folder, which region's card is never told. A
  document kept apart from its footage wires the saved file by the copy buttons and an absolute
  folder. Whether the card should know the document's folder waits on that being met.
