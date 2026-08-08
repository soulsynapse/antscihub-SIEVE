---
title: Composite kinds get their editors
step: "07.8"
status: done
gated_on: nothing
done_when: "uv run pytest tests/gui/test_kind_editors.py -q -k 'a_drawn_region_enters_as_a_set_param or a_dragged_span_enters_as_a_set_param'"
opened: 2026-08-08
---

# Composite kinds get their editors

Handoff services generalize crop-as-contract: a `region` param gets the
canvas-draw surface, `span` gets timeline handles — each an editor bound to a
param field whose output is only a param value, entering as SetParam through the
same path as a typed one (`adr/gui-knows-kinds-not-tools.md`). Editors generate
per kind, never per tool, which is the same asymmetry the widget generator
carries one step up.

`BAND` is the third composite kind and does not get its editor here; the axis
its handles are dragged on is
[a-bands-axis-has-no-vocabulary-and-no-plot.md](a-bands-axis-has-no-vocabulary-and-no-plot.md).
`POINT` has no tool declaring it, so it has no subject either
(`whether-a-stereotype-declares-an-arity.md`'s closing observation).

## Ruled 2026-08-08 at review — the band clause is struck

As opened, this item's second half required "spec data binding the `BAND` field
to a named emit of its own tool … a band whose named emit is not one its tool
declares fails loud". The worker built nothing and stopped on it, correctly.
`detect` is the only tool on the shelf carrying a `BAND`, it carries three, and
its registration comment (`tools/detect.py`) says in its own words that the
series those three are dragged on never leave the node: `emissions` is exactly
`(Emission("gate"),)`. So the required binding would have `detect` declare
`"gate"` three times — a declaration verified as well-formed and false, which is
what `adr/declared-means-verified.md` exists to refuse — and the optional
binding would leave the only band-carrying tool without an editor and the new
field with no consumer but its own test. Widening `emissions` is not a way out:
`_check_emissions` requires a multi-product list to be exactly one closed-set
selector's values, and these are intermediates nobody picks.

The clause also contradicted a ruling already settled at phase 1.
[a-band-has-no-stereotype-of-its-own.md](a-band-has-no-stereotype-of-its-own.md)
refused a declared axis on grounds this item never engaged — `freq_band` is Hz,
`value_band` is in the upstream node's output units and so is not knowable at
spec time, `count_frac` is dimensionless — and left *which* plot undeclared
deliberately. Nothing linked the two items, and nothing goes red for that.

What stays here is the region/span half, which is what `PLAN.md`'s Phase 7
paragraph actually lists and which needs no vocabulary that does not exist.
