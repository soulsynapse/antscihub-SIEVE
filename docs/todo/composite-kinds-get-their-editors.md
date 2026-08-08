---
title: Composite kinds get their editors, and a band's axis is a named emit
step: "07.8"
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui/test_kind_editors.py -q -k 'a_drawn_region_enters_as_a_set_param or a_band_editor_sits_on_its_declared_emit' && uv run pytest tests/unit/test_tool_contract.py -q -k a_band_axis_names_an_emit"
opened: 2026-08-08
---

# Composite kinds get their editors, and a band's axis is a named emit

Handoff services generalize crop-as-contract: a `region` param gets the
canvas-draw surface, `span` gets timeline handles, `BAND` gets handles on the
graph panel — each an editor bound to a param field whose output is only a
param value, entering as SetParam through the same path as a typed one
(`adr/gui-knows-kinds-not-tools.md`). Editors generate per kind, never per
tool, which is the same asymmetry the widget generator carries one step up.

This is where the axis `adr/one-field-is-one-populated-value.md` deliberately
left undeclared gets declared, because the editor is the reader that cannot
proceed without it: band handles sit on the value axis of a specific series,
and nothing in the spec says which. The declaration is spec data binding the
`BAND` field to a named emit of its own tool — the vocabulary
`a-tool-declares-what-it-can-emit.md` minted — proved at registration: a band
whose named emit is not one its tool declares fails loud
(`adr/declared-means-verified.md`). That keeps the growth where ADR-12 wants
it: the vocabulary grew one binding, and every tool that declares a band from
now on gets its handles for free.
