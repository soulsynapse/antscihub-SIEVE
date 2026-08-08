---
title: The generator builds widgets from stereotypes, and the constraint walk is written once
step: "07.5"
status: done
gated_on: nothing
done_when: "uv run pytest tests/gui/test_param_generator.py -q -k 'a_widget_per_kind_never_per_tool or an_unknown_kind_is_refused_by_name' && uv run pytest tests/unit/test_inspect_cmd.py -q -k a_composite_param_prints_its_bounds"
opened: 2026-08-08
---

# The generator builds widgets from stereotypes, and the constraint walk is written once

One generator reads each param field's presentation stereotype and emits a
widget per kind, wired to emit SetParam through 07.3's layer — adding a tool
adds zero GUI code unless it declares a new kind
(`adr/gui-knows-kinds-not-tools.md`). This is the reader the stereotypes have
waited for since Phase 1: the stand-in consumer refused an unknown kind by
name at registration, and the generator now owns that refusal at the surface
too. `adr/one-field-is-one-populated-value.md` is what makes the mapping
one-to-one — a composite kind hands the generator one field holding the whole
value. v2's `param_form.py` is the seed (PLAN.md, port disposition).

`a-composite-parameter-prints-no-shape-and-no-bounds.md` folds in here and its
file is gone: bounds and shape live in `params_model`'s JSON Schema, where a
composite field's constraints sit under `anyOf`/`$ref` one level down, and
both readers — `sieve inspect` and this generator — degrade to `any` without
the walk. The walk is written once, Qt-free, beside `params_model` in
`core/tool_base.py` (no new `core` child; `adr/core-membership-is-closed.md`
stands), and inspect re-points its `_CONSTRAINT_KEYS` read through it — so
`crop`'s region and `detect`'s `count_frac` print their bounds in the terminal
the same commit the generator learns to build their widgets. A second
description of the parameter space anywhere is the drift that folded item
existed to refuse.
