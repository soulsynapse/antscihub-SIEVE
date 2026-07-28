---
title: "Click-through navigation: the output boundary lives in the chain-stack"
status: deferred
after: [materialization]
gated_on: >
  general materialization promoting (docs/todo/materialization.md) — the
  source-boundary half left this item 2026-07-28 and shipped
  (docs/completed-todo/2026.07.28-crop-boundary-gesture.md), and what remains
  here is descent through *node* output boundaries, which has no writer until
  the general store exists
reads:
  - docs/REFINED-VISION.md
  - docs/SETTLED.md
  - docs/todo/sink-writers.md
  - docs/todo/materialization.md
  - src/sieve/gui/replicate_table.py
  - docs/ARCHITECTURE.md
---

# Click-through navigation: the output boundary lives in the chain-stack

**Split 2026-07-28, and the source half has since landed.** The *source*
boundary — the replicate crop — moved out and was built the same day
(docs/completed-todo/2026.07.28-crop-boundary-gesture.md): the
card, the four states, and the write pass. Everything the two boundaries share
is therefore no longer a design question here but a shipped mechanism to match —
the four-state reading, the write-with-progress, and the deliberate register a
materialize offer sits in.

**The freeze is not among them, and that is a correction to this item.** The
source boundary shipped freezing the backed replicate's box and the clip, with
discard as the only way back, and that was removed later the same day: an
artifact is an acceleration, and one that refuses the tuning it exists to
accelerate has inverted its purpose. Both edits already fail safe without a
gate — a moved box misses `CropArtifact.backs`, a window outside the cut misses
in `resolve_source`, and the render falls back to the parent with the same
pixels under the same keys — so what the user gets is a `STALE` card naming the
clause that missed. The cut is also taken over the whole source rather than the
working window, which is what makes moving the window free. **A node boundary
must answer the same question for itself**: descent below a materialized node
output is not obviously the same shape, because there the ancestry is *the
thing being displayed as at rest*, and "faded means frozen" is still the rule
if anything is faded at all. What is no longer available is citing the source
boundary as precedent for freezing.

This item keeps only what remains: descent through
*node* output boundaries, the fading ancestry above one, the suggestion
machinery, and the sibling question. One premise shifted with the crop's
identity model (child source, not byte-exact stand-in): a materialize offer is
result-*changing*, so the suggestion division below keeps its two registers but
"checkpoint this stage" no longer sits in the casual one.

REFINED-VISION's replicates section ends with two sentences about a different
tab: "Right click on the video in the filters tab goes back up to the source.
Left click on the video in the filters tab advances forward in outputs." Neither
exists — `gui/filter_tab.py` and `gui/composite_view.py` install no mouse
handlers at all, and step navigation is the chain-stack list.

**The design (revised 2026.07.27, superseding the breadcrumb).** The output
boundary is an element *in the chain-stack itself*. Clicking through it
descends: everything above fades, and the faded ancestry is the breadcrumb —
it shows content where a breadcrumb bar shows names. Scrolling up and clicking
a faded stage re-ascends. Fading binds behaviour, not just appearance: faded
means frozen (rule 6's mirror direction), because a stage above a materialized
boundary can no longer be edited without editing the identity of something at
rest — so unlocking a faded stage is an explicit discard of the artifact below,
never a silent invalidation. REFINED-VISION's "SIEVE forgets everything above
it" is kept where it mattered — the child artifact is computationally
self-contained and readable without the parent — and deliberately weakened for
display, where amnesia served nobody.

**Why the earlier substitute stays rejected.** The tempting build was to bind
the two clicks to the chain, up a step and down a step over `Dag.order`, which
is expressible today. It is still the wrong thing, and the reason generalizes:
*gestures bind to axes, not widgets.* "Leave this context for a narrower one"
and "look at the previous node's output" are different operations, and spending
the click on the second means the first arrives later needing the binding back,
after users have learned it. The 2026.07.27 design succeeds not by rebinding
the gesture but by relocating the output axis's objects into the widget — the
boundary element genuinely lives on the output axis, so the click's meaning
never changes, and it matches the replicate tab's left click, which already
means accept-and-descend.

**Why it is one item with materialization, not a follower of it.** Compaction
is user-initiated, never automatic (settled in the deferred **Materialization**
item, docs/todo/materialization.md), and this gesture is the initiation:
clicking through an unmaterialized output boundary is the offer to materialize
it, and the descent lands when the writer finishes. Before the writer exists the
descent must refuse rather than fake — a faded "at rest" ancestry that is
actually recomputed per frame is rule 6's failure verbatim. The source boundary
has already been through this cycle and is what the node boundary should copy:
offer, write with progress and cancel, register — `gui/chain_stack.py`'s
`SourceCard` and `gui/materialize_worker.py`.

**The standing request this rejection is answering** (noticed `<=2026.07.27`,
folded in here 2026-07-28 from its own item, which was one file holding one
rejection): "right click on the video in the filter tab should take it back to
the replicate tab full view." Mechanically it is small —
`_CompositePane.mousePressEvent` already handles presses and the tab switch is
a signal out of `StepCompositeView` — which is exactly why it needs an argument
against it rather than a backlog position. Building it puts a second,
undocumented navigation affordance on the same surface, and the two would have
to be reconciled the first time either moved. Either this item revisits the
rejection (a right-click *plus* the boundary is defensible if they mean the
same thing), or the boundary lands and closes the request rather than building
it. If it is built anyway as a knowingly provisional stopgap — a legitimate
call — the completed entry has to say so, because an unlabelled provisional
binding is what makes the reconciliation expensive. And "back to the full view"
must define what happens to the current selection and window: returning without
carrying the selected replicate is a different gesture from the one being
asked for, and the difference is invisible until someone has two replicates.

**Suggestions ride the boundary, divided by rule 7.** The boundary element is
where the system may propose insertions — and every proposal sits on one side
of the identity line. Result-preserving (checkpoint this stage; never hashed;
accept casually) and result-changing (insert a `rescale` before this output —
`downsample.py`'s docstring already makes the storage argument; changes every
downstream key and partially discards tuning) must never share a visual
register. Suggestions are ignorable (hide) and disableable in preferences; a
dismissed result-changing suggestion stays dismissed per-project, not
per-session, or it becomes a nag about a decision already made.

**What the linear view cannot say.** The folder model permits siblings — two
outputs from one parent. A chain-stack shows one path; the moment a second sink
exists at the same depth, a branch affordance is needed that fading does not
provide. Undecided, and worth deciding before the stack's linearity becomes
load-bearing.

**What would make it the right time.** The same trigger as the replicate
status columns, now folded into the deferred **Sink writers** item
(docs/todo/sink-writers.md), and sharpened: this item and the materialization
item, docs/todo/materialization.md, land as one item, gesture-first.

**The constraint to not get wrong when it lands**, inherited whole from the
deferred **Coverage and detection lanes** item,
docs/todo/coverage-and-detection-lanes.md: *absent* and *not yet computed* must
not look alike. An output that does not exist because nobody ran the graph and
an output that does not exist because the graph produced nothing are different
claims, and a table that paints both as an empty cell is the
unexamined-versus-quiet collapse arriving through a third widget.

Read: `docs/REFINED-VISION.md` **Replicates**,
`docs/completed-todo/2026.07.25-replicate-tab.md`,
the deferred **Sink writers** item, docs/todo/sink-writers.md, the
**Materialization** item, docs/todo/materialization.md,
`src/sieve/gui/replicate_table.py`, `docs/ARCHITECTURE.md` rules 6 and 7.
