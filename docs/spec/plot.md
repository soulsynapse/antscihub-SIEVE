# Plot: one plot under the frame is the seek bar, the selection owns its axis, the pinned ride along in ink

Written 2026-11-10 from Kendrick's mockups of that day and the conversation that read them, on v5
at 694aff59; no box is ticked. Read with sieve_player/widgets.py, whose Trace and Density are the
plots this spec moves and the live statement of how a series is drawn losslessly; with
sieve_player/timeline.py, whose Strip is the whole-clip view the plot is the windowed twin of; with
sieve_player/pane.py, which today holds every plot inside its node's card and the pin in the card's
corner; with sieve_player/document.py, where the pinned flag and a node's band live; and with
docs/spec/bake.md's Reading back, which settled that a series is drawn at its rows and never
stretched. The theme's rule that a rendering neither hides nor adds a value holds throughout: a
column is its rows' envelope, a series scaled to its own range is the same series, and a value is
read by pointing, never by a shared scale that does not exist.

## Why

A series indexes the frame by time, and today the plot that draws it sits in the right column,
inside the settings card of its node, as wide as the pane and a screen's width from the frame it
indexes; the pinned one is drawn a second time, at whole-clip scale, under the timeline's handle.
Every editor whose x axis is time puts the track under the viewer, and a user arriving from an
editor, an audio tool or a trace viewer scrubs in the plot without being told. Kendrick's second
mockup shows the shape: one plot the width of the frame, flush with its bottom edge, the playhead a
circle astride that edge as a phone player's position dot is astride its bar, the hover a dotted
line down the plot with each series' name and value beside the point it crosses, and a row of
name chips along the bottom, right-justified, each with its pin, that is the legend, the selector
and the pinned set in one strip.

One plot rather than a stack, because every plot under the frame is taken from the frame, which is
the thing being looked at, and a user who pins three series should not watch the video shrink
three times. Several series share the one plot by overlay, and the overlay is honest about what it
can show: shapes align in time, and magnitudes are read by pointing. The y axis belongs to the
selection and nobody else; a pinned series is drawn dimmed, scaled to its own range over the full
plot, with no axis, and which it is and what it reads is what the readout beside the hover dot
says. Colour in the theme says what kind of thing, a type on a connector, a role elsewhere, and
never which one; which one is a name, in the plot as on the canvas, so no node has a colour of
its own and the pinned are told from the selection by ink against the series colour, and from one
another by the hover and the chips. Decided 2026-11-10. A field, a
density today, is drawn under the lines and at most one at a time, a spectrogram under a pitch
contour: overlaid fields are only denser, and do not read.

The settings go back to the right column, under the canvas, where the pane is today. Plots and pins
leave the cards; a card is a node's settings and standing and nothing else.

## How to read this

Each `##` below is a deliverable: an `Assumes:` line naming what it builds on, a sentence of why,
facts read off the tree, then done-when assertions, each a box with a `Check:` that is a test in
`tests/`. A box is ticked by a session once its test passes in the tree; a session never unticks or
rewrites an assertion, and before building toward an unticked box checks whether the tree already
meets it. Where a result is worth Kendrick's eye before the next deliverable leans on it, a `Worth
a look:` line says what to look at; it is not a gate. Nothing here says how. Any deliverable whose
`Assumes:` are all done is available; among those the earlier one in the file first. The branch is
done when every box is ticked.

Words. The *frame* is the Display, the decoded row with its overlay and drawers. The *plot* is the
one widget under the frame. The *selection* is the node the canvas last selected, as the pane
shows it today. A node is *shown* in the plot when it is the selection or is pinned, and has a
result the walk produced. A *line* is a series node's signal, drawn as Trace draws it; a *field*
is a frame node's density, drawn as Density draws it. The *pinned set* is the nodes whose pin is
on, kept in the document in the order they were pinned. The *chip row* is the row of name chips
along the plot's bottom. The *window* is the loop window of the timeline, the plot's x axis as it
is every Trace's today. The *strip* is timeline.py's.

## The pinned set

Assumes: nothing.

The one flag today draws one series under the strip's handle; the plot shows every pinned node
beside the selection, so the document holds the set, in pin order, and the strip reads the same
set.

Facts to weigh. `Document.pinned` is one node id or None, written only when set, cleared by
`remove` when its node goes; the pane's `_pin` moves the flag and rechecks every pin, and the
window's `_show_pinned` hands the strip that node's signal, the clip walk's when there is one.
Every series node's card carries a pin; no frame node's does.

- [ ] The document holds the pinned nodes as an ordered list, any node with a plot, and writes
  none when it is empty; a format-2 file's one pinned id loads as a list of one; a removed node
  leaves the list.
  Check: a document test pins two nodes, reads them in order, removes one, round-trips, and
  loads a format-2 file with `"pinned": "<id>"` and reads a list of that one.

## The plot under the frame

Assumes: nothing.

The plot is where a user scrubs, so it sits where the frame's time is read, the frame's width,
flush with its bottom edge, and nothing else under the frame.

Facts to weigh. `PlayerWindow` lays the Display and a `Column` of canvas over pane in a horizontal
splitter, and the Timeline across the bottom; the Column caps the pane at `SHARE` of its height.
Every Trace and Density is built in `Pane._build` inside its node's card, hidden until the walk
hands it a result, and the window's `_hook_traces` finds them with `findChildren` to wire seeking
and hover; `Pane.sizeHint` is the shown card's height. A Trace is `ROW_H * rows` tall, a series
trace five rows and a density six. A Trace's field is inset by its handles' room so stacked
traces share x, which the one plot no longer needs. Display's `minimumSize` is 160 by 120.

- [ ] The left of the splitter is the frame over the plot, the plot the frame's width, the two
  flush, and the plot's height fixed; the frame takes the rest. No card in the pane holds a plot
  or a pin, and the pane's height is its settings' alone.
  Check: an offscreen window test reads the plot's top equal to the frame's bottom, its width the
  frame's, and no Trace, Density or pin button among the pane's children.
- [ ] The plot draws the selection when it has a result, as Trace or Density draws it today, and
  the pinned set with it; a selection without a plot, the video node or a blobs node, leaves the
  pinned set drawn and the plot otherwise empty but for the playhead and the ruler. The plot's x
  axis stays the window, filling in as the walk does.
  Check: a window test selects a series node and reads it drawn, selects the video node and
  reads the pinned nodes still drawn.

## The playhead and seeking

Assumes: The plot under the frame.

The circle astride the frame's edge is what makes the frame and the plot read as one object, and
the plot is the seek bar because it is under the thing time moves.

Facts to weigh. A Trace press anywhere but a handle is the playhead, `pressed`, `dragged`,
`released` in rows, and the window's `_scrub_begin` pauses play while it is held; the strip does
the same and the two are wired alike. The Display draws the playhead nowhere; the time bubble,
"439.20 s" in the mockup, is the strip's `_show_bubble`, a tooltip the strip owns.

- [ ] The playhead is a white line down the plot at the row, topped by a filled circle centred on
  the frame's bottom edge, half over the frame; a press on the circle or anywhere in the plot
  that is not a handle seeks, dragging follows, and play pauses while held, as a Trace does today.
  Check: a window test presses in the plot, reads the row sought and play paused, drags, reads the
  row follow, releases.
- [ ] A ruler along the plot's top edge marks time in seconds at a spacing that keeps labels
  apart, the window's start and end among them.
  Check: a plot test sets a window and reads tick rows within it, the first at its start.

## The selection owns the axis

Assumes: The plot under the frame.

One series is read at full strength, with the numbers that let it be read, and the band is the
selection's to tune; everything else is context.

Facts to weigh. A Trace's field height is the series' maximum, a handle dragged to the top is
infinity, and the band's values today are drawn as readouts at each line's right end, with the
corner readout the value under the cursor; `EXCLUDED` darkens what the band shuts out and `GATED`
washes the kept rows. A band moves through `levelDragged` and `levelReleased`, the pane's
`_banded` writing it to the node and emitting `paramsChanged`. A Density's two handles are a
band of the plane's values and crop the picture as they move.

- [ ] The selection is drawn as a Trace or Density draws today, teal, or green with a gate, with a y axis along the plot's left edge in
  the selection's units, labelled at a few values, and a gutter so the curve does not overprint
  the labels. Its band is two lines across the plot with handles, drawn in `LEVEL` as today, and
  each band value is a label on the axis in `LEVEL` at the line's height; no readout sits on the
  line. The gate wash and the excluded darkening are the selection's.
  Check: a plot test sets a selection with a band and reads two axis labels at the band's
  values and none elsewhere on the line.
- [ ] Dragging a handle changes the selection's band, saved to its node as today; while a handle
  is held every other shown node fades to near nothing, and returns on release.
  Check: a plot test presses a handle and reads the pinned series' alpha below a threshold, moves
  it and reads the band in the document, releases and reads the alpha restored.

## The pinned ride along

Assumes: The selection owns the axis; The pinned set.

Several series on one plot align in time, and are read by pointing.

Facts to weigh. `Trace.paintEvent` draws one series as its columns' envelope; a second series is a
second envelope over the same rows, each scaled to its own maximum. A pinned node whose result
the walk has not produced has nothing to draw, which `Pane.show_series` hides today; `KIND`
"same" takes both plots.

- [ ] Each pinned node other than the selection is drawn as a line in ink at one reduced alpha,
  the same for every pinned node, scaled to its own range over the full plot height, with no axis,
  no handles and no band lines, its band drawn as the darkening alone; a pinned node without a
  result is not drawn. A pinned node that is the selection is drawn once, as the selection.
  Check: a plot test pins two series of different ranges, reads each spanning the plot's
  height and drawn in the same colour, and selects one and reads it drawn once in the series
  colour.
- [ ] At most one field is drawn, under every line, dimmed when it is not the selection; pinning
  a second field unpins the first. A field that is the selection is drawn as Density draws it,
  its handles the selection's.
  Check: a document test pins two frame nodes and reads the first gone from the pinned set; a
  plot test selects a series over a pinned field and reads the field drawn first.

## The hover

Assumes: The pinned ride along.

Magnitudes are read by pointing, so every shown node answers at the cursor's row.

Facts to weigh. A Trace reports `hovered(row)` and draws another widget's cursor through
`set_hover`; the window's `_hover` sets one row on every trace and the strip, and a Density's
readout is the value of the bin under the cursor.

- [ ] A dotted line runs the plot's height at the cursor's row, and the strip draws the same row;
  where the line crosses each shown line a dot is drawn, with the node's name and the value at
  that row beside it in the monospace face, the selection's in the series colour and the rest in
  ink; two readouts that would overprint are pushed apart. The field's readout is the value of
  the bin under the cursor, as today.
  Check: a plot test sets a hover row and reads one readout per shown series carrying that
  series' name and value at the row; a test with two series equal at the row reads the readouts
  not overlapping.

## The chip row

Assumes: The pinned ride along.

The legend, the selector and the pin are one row, because they are three views of one set.

Facts to weigh. The canvas's `selectionChanged` hands the pane the last id and nothing else is
told; `GlyphButton("pin", ...)` is the pin today, checkable. The Tab menu is sized to its rows; the
theme's `ROW_H` is every control's height.

- [ ] A row along the plot's bottom edge, right-justified, holds one chip per shown node, the
  selection first then the pinned in pin order, each the node's name with a pin glyph beside it;
  the selection's chip is in head white, the rest in ink. A click on a chip's name selects
  that node, as a click on the canvas does, and the canvas shows it selected. The pin glyph reads
  on or off, filled or outline, and a click toggles the node in the pinned set; the selection's
  chip shows whether it will stay when another is selected.
  Check: a window test selects a series and reads its chip first and bright, clicks a pinned
  chip's name and reads the canvas selection moved, clicks the selection's pin and reads the node
  in the pinned set, selects another and reads the first still shown.

## The strip mirrors

Assumes: The pinned ride along; The chip row.

The pinned set is one set at two zooms, and nothing a pin means changes between them.

Facts to weigh. The strip draws one series, `SERIES` or `GATE`, as its columns' envelope over the
whole clip, the clip walk's when it has one, else the window's at its own rows; `_show_pinned` is
where the window hands it over.

- [ ] The strip draws every shown node, the selection as it draws its one series today and the
  pinned in dimmed ink, each as its columns' envelope at its own range, with no axis; a field is
  not drawn in the strip.
  Check: a window test pins two series and reads two series handed to the strip with the
  selection marked; a timeline test draws two and reads each at its rows.

## Non-goals

- A stack of plots, or lanes within the one plot. One plot, overlaid; a series scaled to its
  own range spans the whole height.
- Overlaying two fields. One under the lines; a second pin replaces the first.
- A wavelet or any other two-dimensional series plot. When one lands it is a field under this
  spec's rule and nothing here changes.
- Reordering chips, or pinning by drag. Pin order is the order pinned.
- A colour per node. Hue says a type or a role and never an identity; if the dimmed ink proves
  not enough in use, the fallback is a reserved identity gamut no type or role colour draws from,
  decided then on the evidence.
- A plot of the whole clip. The strip is that view and stays the timeline's.
- The time bubble over the frame. The strip's bubble is the one readout of the playhead's time.

## Open

- The plot's height: a fixed number of rows, or dragged against the frame. Fixed to begin with;
  which number waits on the first build being looked at.
- Which side the axis sits on. Left in the mockup and here; the right edge is where a Trace's
  band readouts sat, now gone, so either is free.
- Whether a chip row with nothing pinned and a selection without a plot shows anything, or the
  row collapses to nothing.
