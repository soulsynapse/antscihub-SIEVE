---
title: The command layer is the document's only writer, keyed by intent kind
step: "07.3"
status: deferred
deferred_for: decision
gated_on: Kendrick ratifying the intent-kind list — the argument is in the body, and it amends the list PLAN.md's Phase 7 states and VISION.md cites as the definition of a complete GUI
done_when: "uv run pytest tests/unit/test_intents.py -q -k 'a_set_param_intent_lands_as_a_new_whole_value or set_outputs_moves_no_cache_key'"
opened: 2026-08-08
---

# The command layer is the document's only writer, keyed by intent kind

One layer, Qt-free, sitting on 07.2's session: every mutation of the open
project enters as an intent, lands as a new whole pipeline value on the undo
stack, and nothing else writes — dissolving v2's `document.py`/`commands.py`
co-change (PLAN.md, Phase 7).

The deferral is the kind list. PLAN names SetParam, DrawRegion, SetSpan,
AddNode, and two settled decisions have hollowed half of it since it was
written: `adr/one-field-is-one-populated-value.md` makes a span one pair-shaped
param, and `adr/gui-knows-kinds-not-tools.md` makes a drawn overlay an editor
bound to a param field "entering through the same command path as a typed
value". So DrawRegion and SetSpan name emitting surfaces, not document
mutations — as kinds they would key the layer by which widget produced the
value, which is the coupling the layer exists to dissolve. The recommended
list enumerates mutations of the saved file instead:

- **SetParam**, addressed by node, param, and an optional replicate — an
  override is the same mutation at a longer address, not a second kind, so a
  canvas drag on a replicate emits SetParam like everything else and no editor
  branches on selection state that belongs to the view.
- **SetOutputs** — the checkoff writes `Project.checkpoints` and
  `Project.outputs`, and it enters here or the save screen becomes a second
  writer. Its test is Phase 2's reason those fields live on `Project`: no
  cache key moves.
- **AddNode / RemoveNode** arrive with the surface that emits them, which the
  first cut does not build (it opens a project that exists) — a kind no
  surface emits is a declaration without a consumer
  (`adr/declared-means-verified.md`).

VISION's completeness claim then reads: a layout is operational when every
kind has an emitting surface and every composite stereotype has an editor.
Ratifying this edits PLAN's list, which is why the item waits rather than
takes it.
