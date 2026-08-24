# The tuning loop — the plan in phases

Not a finding and not an ADR. The route from a substrate that runs to the thing
it was built for: a crop somebody draws, steps that run over it, and the numbers
that say whether any of it is working. Kept only while it is being walked — a
phase leaves this file when its code lands, and the file follows
`docs/archive/2026.08-substrate-port.md` into the archive when the last one
does. Numbers are cited to the finding that holds them and never restated here.

## Where the structure comes from

`mockup/mockup.py` is the interface as it is meant to be, in one runnable file
with mock data. It is read here for **structure** and never for implementation:
what the screens are, what a card holds, what a control is *of*. The primitives
it draws with are `mockup/paper_primitives.py`'s, and the tree's own are
`src/sieve/gui/primitives/`, which are settled and are what anything built here
uses.

**The mockup is ahead of the ADR record and says so out loud.** `_crop_pair`
cites "ADR 12"; this tree has eight. So some of what the mockup treats as
decided has never been written down here, and a phase below that leans on one of
those decisions is leaning on something with no home. Where that happens it is
named, because the alternative is a plan that quietly promotes a mockup comment
to a settled decision.

## What the mockup settles, and what it collides with

**A crop is normalised, and a form is in pixels.** The mockup's editors are
percentages, on the stated grounds that "a source of another size would make a
pixel field lie on load". `frame.form.Form.rect` is source pixels, on the stated
grounds that pixels survive every downstream resampling. Both are right about
their own layer and the two must not be conflated: **normalised in the document
and the editor, pixels in the form**, converted at one boundary that is named
once. A conversion that happened in two places would be the rounding rule all
over again — that one was written twice, disagreed with itself by two pixels,
and produced two keys for one picture.

**A crop step cuts several regions, and this is the real gap.** The mockup has
`CROPS`, a selected index, and four number boxes that edit "whichever region is
selected, not a region". The declaration layer has no answer for that:
`analysis.tool.Tool.form_for` takes one rect and returns one `Form`, so a step
with three regions has one form and cannot say what it is about. Everything
downstream inherits it — `residency` is over `(row, form key)` pairs, a series
is keyed by one form, and the producer gathers inputs for one form. This is a
fork rather than an oversight and it is the first thing to settle.

**One clamping setter, and every editor pulls.** A crop is written through a
single function that clamps it onto the frame and keeps a minimum area, and then
every editor is told to re-read — *including* one a clamp moved, "or the field
would keep claiming a crop the pipeline never had". The watcher list is keyed by
owner widget and unregisters on destroy, because cards are rebuilt on every walk
move and a callback holding a deleted spin box is a crash.

## Primitives the tree is missing

Two, both wanted by the crop card, and both currently drawn ad hoc.

**A number box.** The mockup uses a bare `QDoubleSpinBox` with a range, a step
and a suffix. The tree's nearest is `primitives/field.py`'s
`LineField(numeric=True)`, which right-aligns a line edit and is not a stepper.
What the crop needs is a *value with a unit inside a range that can be typed
into or stepped*, and which can be pushed a corrected value after a clamp
without re-emitting. That last property is the one that makes it a primitive
rather than a widget: everything that edits a clamped quantity needs it.

**A small icon button.** The `+` and `−` beside the crop count, and the `+` in
the library's head, which is already a hand-rolled `QToolButton` with a
stylesheet in `project_list/view.py` — and the swipe's arrows, which are a
second hand-rolled pair in `frame/swipe.py`. Three copies is the point at which
the tree usually settles one. `primitives/button.py` is text in four weights and
deliberately says nothing about icons.

Not proposed: `paper_primitives` also has a `Switch` and a `unit_field` with no
settled counterpart. Nothing below needs them, and a primitive minted before a
second caller exists is a guess about what the second caller will want.

## Phases

Each names what it owns, what it may not know about, and what proves it — the
same shape the port plan used, and the same rule for evidence: a harness script
under `experiments/substrate-checks/`, with a `--broken` mode, because a check
that has never failed has no demonstrated power.

### T0 — the crop, as a value

`src/sieve/analysis/crop.py`, and the fork above settled first.

Owns what a crop *is*: normalised regions, which one is selected, the clamp, and
the conversion to a `Form` in source pixels. No Qt, no widgets, no watchers —
those are T1's. A pure value with a pure clamp is a table of cases, and the
clamp is the part everything else trusts.

*Proves it:* a region stays on the frame and keeps its minimum area under every
drag the interface can produce, including ones that start outside it; a rect
round-trips normalised → pixels → normalised within a pixel; two sources of
different sizes give the same normalised crop different pixel rects and the same
`Form.key` only when they should.

### T1 — the crop, on the canvas

`src/sieve/gui/view/canvas/overlay.py`, `primitives/number.py`,
`primitives/icon_button.py`

Owns drawing the box over the stage and dragging it, the four number boxes, the
region count, and the one notification that keeps them agreeing. The stage rect
already comes from `canvas/view.py`'s `staged` signal, which exists so that
"what a crop box is drawn against is the same rectangle the content was placed
in" rather than each layer working it out and agreeing by luck.

*Proves it:* a clamped drag comes back to the boxes as the clamped value; typing
a number the clamp moves shows the moved number; selecting another region
repoints the same four boxes; a watcher whose widget is destroyed is gone.

### T2 — a step that runs

`src/sieve/analysis/steps.py`, and the session's tool set

Owns the first real step. `absdiff` and `dis_flow` come across from
`experiments/tool-experiments/tools.py` **with the comments they earned** — a
thread-local DIS solver rather than a lock, `cv2.magnitude` rather than a numpy
norm over the channel axis, `convertScaleAbs` rather than a float multiply that
silently promotes a whole image to double. Each of those was a wasteful field
implementation the cost experiments caught.

This is where the producer stops being idle: a step declares, the frontier
admits at the step's form, and `analysis.record` writes a series. Everything for
that is built and checked already; what is missing is a step.

*Proves it:* `11-provenance` gains a real step and, for the first time, runs its
invariant over a real decode rather than the fake route — which the archived
plan records as still owed.

### T3 — the numbers

The predicted re-fetch, the account, and where they surface

Owns ADR-0008's instrument, which is the last thing in that ADR with no
implementation. `ledger.waste` has exactly one caller; the count that makes a
declaration falsifiable needs a declaration in play, which T2 provides. The
account and its unattributed remainder are built and nothing reads them.

Where it surfaces is settled and not this plan's to re-decide: a small indicator
where the work is, the account itself in the walked step's own pane, which is
the third position on the track (ADR-0008, ADR-0003).

*Proves it:* a session driven through a landing, a crop change and a scrub
reports zero predicted re-fetches; `--broken` re-introduces the point-set
residency and the count rises, which is `05-declarations`' figure arriving in
the running application.

### T4 — the proxy, running

Owns starting `ProxyBuilder` from the session and letting the hunt tier answer
from it. All of it is built, checked against a fake launcher, and driven once by
hand against real ffmpeg; nothing in the application starts one. The display
form the loop already plays is the proxy's form, so a finished segment answers
the loop directly — which is the whole reason that width is one number.

*Proves it:* with a proxy present, hunting outside the window serves `proxy`
rather than `keyframe`, and the served frame is refused admission because a
display form that has already been resampled can only ever be shown.

## Not in this plan

**The chain.** The mockup's pipeline — a rail of nodes, per-step cards, the
sliding panes, the band plots — is the second and third positions on the track,
and it is a great deal more than the loop needs to be tunable. It wants its own
plan once a single step runs end to end and there is something to chain.

**Scrubbing and landing elsewhere.** The transport loops a fixed window. Moving
the playhead outside it is what the hunt tier and the proxy are for, so it
follows T4 rather than leading it.

**The library's missing verbs.** `Library.forget` has no way to be reached, and
nothing offers to remove a recording from the list. Small, unrelated, and worth
doing whenever the library is next open.
