# The tuning loop — the plan in phases

Not a finding and not an ADR. The route from a substrate that runs to the thing
it was built for: a crop somebody draws, a step that runs over it, and the
numbers that say whether any of it is working. Kept only while it is being
walked — a phase leaves this file when its code lands, and the file follows
`docs/archive/2026.08-substrate-port.md` into the archive when the last one
does. Numbers are cited to the finding that holds them and never restated here.

Every claim below is sourced to a file in this tree that was read for it. Where
something is genuinely undecided it says so rather than being filled in.

## What is already settled, and where

**The crop, by the explorers.** `experiments/tool-experiments/tool-explorer.py`
draws one, maps it, applies it and lives with the consequences; the storage
explorer does the same. That is the design, and the phases below build what
those two do.

**Forms and declarations, by `forms.py` and `tools.py`**, carried into
`src/sieve/frame/form.py` and `src/sieve/analysis/tool.py` and checked in
`experiments/substrate-checks/`.

**The substrate, by the port**, which is done: eight phases, eleven checks, each
with a `--broken` mode.

`mockup/` is visual reference for a previous version and is not read for
structure. One thing was taken from a glance at it and is named where it is
used: the crop's four numbers want a spin box with a unit and a range, and the
tree has no primitive for one.

## What the explorers actually do with a crop

**One rect, in source pixels, even-aligned.** `Form.rect` is x, y, w, h in
source pixels. The explorer clamps a drawn rect onto the frame, floors it at
`MIN_CROP`, and rounds every edge down to even — `yuv420 wants even`.

**Drawn against the whole frame, and refused anywhere else.** The gesture is
rejected unless the full-frame view is up, in words rather than silently: a
rectangle dragged over a cropped view is about a picture that is already a crop,
and the arithmetic back to source is a different sum.

**The widget emits its own coordinates; the owner maps them.** `CropCanvas`
emits the rect in label coordinates "because only it knows what the label is
showing", and the mapping to source pixels — offsets, scale, clamp, even-snap —
belongs to whatever knows how the picture was placed.

**Applying one stops things and re-lands.** The explorer stops playback, stops
the fill, drains the encode queue, drops its windows, and then **re-lands at the
same position**: *"the app never stops: new form, same place."* That last line is
the whole feel of the gesture.

**It also wipes both stores, and the port must not.** The explorer wipes because
its store is keyed by row alone and every frame in it is now the wrong picture.
The port's stores are keyed by `(row, form key)`, so a crop change is a miss
rather than an erasure, the old crop's frames drain under budget, and returning
to a crop is a hit — `session.set_crop`, asserted by `08-session`'s `crop` case.
Everything else the explorer does on a crop change is still owed.

**The hunt tiers survive.** The proxy and the keyframe route never depended on
the crop, so a crop change costs the window and leaves the timeline alone.

**The crop is the session's and a step derives its form from it.**
`Tool.form_for` takes the crop rect and returns the form that step wants, so one
crop feeds every active step and each may want a different form of it.

## Genuinely open

Two things the experiments do not settle, and neither is invented below.

**What crop a recording opens with.** Both explorers hardcode one rect chosen
for the footage in `video-tests/`. A fresh recording has no such answer, and the
plausible ones — the whole frame, a centred fraction, the last one used — differ
in what the first landing costs and in whether an untouched project fills
anything at all.

**Whether a crop is the session's or a step's.** Today it is the session's, and
`Tool.form_for` reads it. A chain in which one node *is* a crop would make it
that node's, and every downstream form would be about that node's output rather
than about the source. That is a decision about what a chain is, so it belongs
with the chain and not here.

## Settled in the experiments and not yet in `src/`

Found by comparing the explorers' constants and mechanisms against what the
port carried, rather than from memory. Each was measured or argued for once and
would otherwise be re-derived — which has already happened once, to the crop
clamp, at the cost of three commits.

**The interpreter switch interval** — carried now, into
`sieve.responsiveness`, and the reason it is listed here anyway is that it was
missed for the whole port despite the plan naming it. Both explorers set it at
import; the fill and encode threads starve the drawing thread for a few hundred
milliseconds at CPython's default. Measured while carrying it: it costs about a
fifth of fill throughput, so every parity number taken before this was
flattering this side by that much, and `10-parity` now applies it and says so.

**`admitted_free`** — the count of crops sliced out of a keyframe decode and
kept, because bytes that already exist are never refused. The ladder admits
them; nothing counts them. It is one of the few numbers that says the hunt tier
is doing what it was built to.

**`SignalStrip`** — per-frame motion energy over the display proxy, computed in
the background and drawn under the timeline. The explorer calls it "the hunt's
real feedback channel" and "the product's premise arriving one screen early":
on a fixed camera the frames cannot show where the behaviour is and the signal
can. It is crop-independent — whole-frame, at proxy resolution — so it survives
crop changes untouched, which is what makes it affordable. It belongs with the
designed strip rather than with these phases, and it must not be lost to that.

**`DEBOUNCE_MS = 300`** — how long a signal slider settles before the work
behind it runs. No slider yet; the figure is settled and should arrive with one
rather than be chosen again.

**`SWEEP_CHUNK = 48`** — rows an ordered pass does between yields, so it can be
stopped. There is no sweep in `src/` yet.

**`coarse_draws`** — the count of fields drawn at reduced resolution under load.
One of the three overlay policies the tool folder deliberately kept without
choosing between, on the grounds that the question is real and unanswered.

## The primitive that is missing

**A number box** — a value with a unit, inside a range, typed into or stepped.
`primitives/field.py`'s `LineField(numeric=True)` right-aligns a line edit and is
not a stepper. What makes it a primitive rather than a widget is one property:
it must accept a *corrected* value after a clamp without re-emitting, or the
field goes on claiming a crop that was refused and a push-pull pair oscillates.
Everything that edits a clamped quantity needs it.

Not proposed: the library head's `+` and the swipe's arrows are two hand-rolled
icon buttons. Two is not three, and a primitive minted before the third caller
exists is a guess about what the third caller wants.

## Phases

Each names what it owns, what it may not know about, and what proves it — the
same shape and the same rule for evidence as the port: a harness script under
`experiments/substrate-checks/` with a `--broken` mode, because a check that has
never failed has no demonstrated power.

### T0 — the crop, as a value

`src/sieve/analysis/crop.py`

Owns what a crop is and what may be done to one: clamped onto the frame, floored
at `MIN_CROP`, every edge even. Owns the mapping from a rectangle in some
widget's coordinates to source pixels, taking the placed rect as an argument
rather than reaching for a canvas. No Qt, no widgets — a pure clamp is a table
of cases and it is the part everything above trusts.

*Proves it:* a rect dragged from outside the frame, backwards, or under the
floor comes back legal; every edge of every result is even; a rect already legal
is returned unchanged rather than nudged; the mapping round-trips through a
placed rect whose aspect differs from the source's.

### T1 — the crop, drawn

`src/sieve/gui/view/canvas/overlay.py`, `src/sieve/gui/primitives/number.py`

Owns the box over the stage, the drag that makes it, and the four numbers that
are its other editor. The stage rect comes from `canvas/view.py`'s `staged`
signal, which exists so that what a crop box is drawn against is the same
rectangle the content was placed in rather than each layer working it out and
agreeing by luck. The full-frame rule comes with it, refused in words.

*Proves it:* a drag the clamp moves comes back to the boxes as the moved value;
typing a refused number shows the accepted one; the overlay's rect in widget
coordinates maps to the rect the boxes hold; and a number box pushed a
correction does not emit, which is the loop that would otherwise not terminate.

### T2 — the crop, applied

`Session.set_crop` grows the rest of what the explorer does

Owns the consequences: stop the loop, stop the fill, drain the encode queue,
drop the window, re-land at the same position. Not the wipe.

*Proves it:* after a crop change no thread is filling the old form, the encode
queue holds nothing addressed to it, the playhead is where it was, and the hunt
tiers still answer.

### T3 — a step that runs

`src/sieve/analysis/steps.py`, and the session's tool set

Owns the first real step. `absdiff` and `dis_flow` come across from
`tool-experiments/tools.py` **with the comments they earned** — a thread-local
DIS solver rather than a lock, `cv2.magnitude` rather than a numpy norm over the
channel axis, `convertScaleAbs` rather than a float multiply that silently
promotes a whole image to double. Each was a wasteful field implementation the
cost experiments caught.

This is where the producer stops being idle: a step declares, the frontier
admits at the step's form, `analysis.record` writes a series. All built, all
checked, and none of it has ever run because nothing declares.

*Proves it:* `11-provenance` gains a real step and runs its invariant over a
real decode for the first time, which the archived plan records as still owed.

### T4 — the numbers

Owns ADR-0008's instrument, the last thing in that ADR with no implementation.
`ledger.waste` has one caller; the count that makes a declaration falsifiable
needs a declaration in play, which T3 provides. The account and its unattributed
remainder are built and nothing reads them.

Where it surfaces is settled and not this plan's to re-decide: a small indicator
where the work is, the account in the walked step's own pane, the third position
on the track (ADR-0008, ADR-0003).

*Proves it:* a session driven through a landing, a crop change and a scrub
reports no predicted re-fetches; `--broken` restores the point-set residency and
the count rises, which is `05-declarations`' figure arriving in the application.

### T5 — the proxy, running

Owns starting `ProxyBuilder` from the session and letting the hunt tier answer
from it. Built, checked against a fake launcher, driven once by hand against
real ffmpeg, and started by nothing. The display form the loop already plays
*is* the proxy's form, which is why that width is one number in one place.

*Proves it:* with a proxy present, hunting outside the window serves `proxy`
rather than `keyframe`, and what it serves is refused admission, because a form
already resampled can only ever be shown.

## Not in this plan

**The chain**, and with it the question of whether a crop is a node. Far more
than the loop needs to be tunable, and it wants its own plan once one step runs
end to end and there is something to chain.

**Scrubbing and landing elsewhere.** The transport loops a fixed window; moving
the playhead outside it is what the hunt tier and the proxy are for, so it
follows T5.

**The library's missing verbs.** `Library.forget` cannot be reached and nothing
offers to remove a recording. Small, unrelated, worth doing whenever the library
is next open.
