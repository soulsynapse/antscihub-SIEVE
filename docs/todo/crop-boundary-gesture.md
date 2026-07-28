---
title: The crop boundary in the chain-stack
status: open
opened: 2026-07-28
gated_on: >
  docs/todo/crop-artifact-writer.md and docs/todo/crop-artifact-serving.md
  landing first — this is the face they were built to wear; take the three
  crop items in order
reads:
  - docs/todo/crop-artifact-writer.md
  - docs/todo/crop-artifact-serving.md
  - docs/todo/click-through-navigation.md
  - src/sieve/gui/chain_stack.py
  - src/sieve/gui/filter_tab.py
---

# The crop boundary in the chain-stack

The front half of click-through navigation, narrowed to the one boundary
whose writer now exists: the *source* boundary. The chain-stack gains a card
above `SPATIAL_PREP` standing for what the graph consumes — this replicate's
crop of the source — and that card is where its at-rest state lives and where
materialization is offered. The full design (descent through *node* output
boundaries, fading ancestry, sibling branches, suggestion machinery) stays in
docs/todo/click-through-navigation.md, deferred with general materialization;
nothing here may half-build it.

## The card's states — and rule 6 owns all four

- **Not at rest** (no matching record): the card says the crop is recomputed
  from the source every render, and offers *Materialize* with the honest
  price on the affordance itself: roughly one render to write (the finding's
  46 s luma on the reference clip), ~100x cheaper decode after. The control
  sits here, where the slowness is felt, not in Preferences.
- **Writing**: progress over the span, cancellable; cancel deletes the part
  file and returns to *not at rest*. The preview pool is paused for the
  duration — the write pass *is* a sequential decode of the same footage,
  and running both recreates the bandwidth wall the artifact exists to
  remove (rule 5: the writer borrows the preview's declared share rather
  than becoming an undeclared fourth consumer; no new `concurrency.py` row).
- **At rest**: the stamp — file size, span, format, written-when — and the
  freeze below. This state must be visually *quieter* than an offer and
  *calmer* than progress; at rest is the goal state, not an alert.
- **Stale** (record exists, match fails — moved ROI, re-exported source,
  missing file, widened clip): shows *why* it no longer backs the replicate
  and offers discard or re-materialize. Stale must not look like *not at
  rest* — an artifact that was cut and then orphaned is a different claim
  from one never cut (the absent-versus-unexamined distinction the
  click-through item inherits, arriving at its first widget).

## Materialize is a decision, not a nicety

Under the child-source identity model the artifact is its own source and
descending onto it re-keys downstream work (one recompute, then every render
cheaper). So this control belongs in the *deliberate* register of the rule-7
division that click-through defines for suggestions — not the
accept-casually register the 2026-07-27 notes assumed when byte-parity was
still the plan. Concretely: the affordance states the re-render, and it is a
click on a labelled control, never a side effect of navigation. Compaction
stays user-initiated, never automatic — a descent from the replicate tab must
not itself trigger a write (that variant was considered and rejected: it puts
a minute of encoding behind a navigation gesture and violates the
user-initiated rule).

## Faded means frozen

While a matching artifact backs the replicate, the inputs that would orphan
it — the replicate's ROI in the replicate tab, and the clip handles beyond
the recorded span — render faded, and faded binds behaviour: the edit is
refused with the reason, and *unfreezing is an explicit discard* of the
artifact (one confirmation naming what is discarded), never a silent
invalidation (rule 6's mirror direction; the same argument the lock item
makes, docs/todo/lock-a-visited-replicate.md, and the two should share
mechanism where the document allows). After discard, edits flow again and
the card returns to *not at rest*.

## Checklist

1. `src/sieve/gui/chain_stack.py` — the source card above the stage headers;
   states as above; signals out (`materialize_requested`,
   `cancel_requested`, `discard_requested`), tab applies them (the stack
   stays a view, per its own docstring).
2. `src/sieve/gui/filter_tab.py` — wire signals to a worker running
   `pipeline/materialize.py` off the GUI thread; pause/resume the preview
   runner around it; register the record through the document/commands layer
   (not undoable — the file exists; discard is its inverse gesture).
3. ROI/clip freeze surfaces in `gui/replicate_tab.py` / timeline handles,
   driven by the same match rule the serving item uses (one implementation,
   imported — a second copy is how the card and the freeze disagree).
4. Tests (`tests/gui/`, `pytestmark = pytest.mark.gui`): state transitions
   per match-clause flip; cancel leaves no record and no part file; frozen
   ROI rejects the edit and discard releases it; the stale and not-at-rest
   states render distinguishably (assert on state, not pixels).
5. `docs/todo/click-through-navigation.md` — trim its source-boundary
   paragraphs to a pointer here in the completing commit, so the deferred
   item keeps only what remains deferred.
