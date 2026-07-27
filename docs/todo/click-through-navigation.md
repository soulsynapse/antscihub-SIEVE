---
title: "Click-through navigation: the output boundary lives in the chain-stack"
status: deferred
gated_on: >
  the same trigger as the deferred **Replicate status** item
  (docs/todo/replicate-status-columns.md), now sharpened: this item and
  docs/todo/materialization.md land as one item, gesture-first
reads:
  - docs/REFINED-VISION.md
  - docs/TODO.md
  - docs/todo/sink-writers.md
  - docs/todo/materialization.md
  - src/sieve/gui/replicate_table.py
  - docs/ARCHITECTURE.md
---

# Click-through navigation: the output boundary lives in the chain-stack

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
actually recomputed per frame is rule 6's failure verbatim. So the navigation is
the front half of `pipeline/materialize.py`, not a widget waiting on it.

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

**What would make it the right time.** The same trigger as the deferred
**Replicate status** item, docs/todo/replicate-status-columns.md, now sharpened:
this item and the materialization item, docs/todo/materialization.md, land as
one item, gesture-first.

**The constraint to not get wrong when it lands**, inherited whole from the
deferred **Coverage and detection lanes** item,
docs/todo/coverage-and-detection-lanes.md: *absent* and *not yet computed* must
not look alike. An output that does not exist because nobody ran the graph and
an output that does not exist because the graph produced nothing are different
claims, and a table that paints both as an empty cell is the
unexamined-versus-quiet collapse arriving through a third widget.

Read: `docs/REFINED-VISION.md` **Replicates**, `TODO.md` **The replicate tab**,
the deferred **Sink writers** item, docs/todo/sink-writers.md, the
**Materialization** item, docs/todo/materialization.md,
`src/sieve/gui/replicate_table.py`, `docs/ARCHITECTURE.md` rules 6 and 7.
