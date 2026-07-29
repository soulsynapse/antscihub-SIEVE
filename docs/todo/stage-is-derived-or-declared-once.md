---
title: Stage is derived from the spec, or declared once — never both
status: open
opened: 2026-07-29
priority: low
gated_on: nothing
after: [a-filter-names-what-it-emits]
reads: [src/sieve/gui/chain_model.py, src/sieve/gui/wizard_model.py]
---

# Stage is derived from the spec, or declared once — never both

The chain's grouping (spatial prep, extraction, temporal filter, detection)
is used by the stack and the wizard and declared by no filter. Before adding
a spec field, check what is a function of properties the spec already has:
temporal correlates exactly with the `stateful` set as it stands; detection
is intrinsic once detection is a filter; spatial-prep versus extraction looks
positional. Declare only the residue that is not derivable — a declared copy
of derivable state will drift, which is R3's origin story and `ChainKind`'s
epitaph.
