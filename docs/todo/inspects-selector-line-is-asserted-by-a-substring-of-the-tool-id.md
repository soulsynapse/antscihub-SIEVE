---
title: inspect's selecting parameter is asserted by a substring of the tool id
priority: normal
phase: 5
status: open
gated_on: nothing
opened: 2026-08-07
---

# inspect's selecting parameter is asserted by a substring of the tool id

`test_a_multi_product_tool_prints_all_four_of_its_emissions` closes with
`assert "signal" in output`, meaning the selecting parameter. The tool whose
line it is reading is called `block_signal`, which is printed two lines above,
so the assertion holds with the selector removed from the output entirely.
Verified: collapsing `_describe`'s `chooses` to `""` leaves all three tests in
`tests/unit/test_cli_inspect.py` green.

What that leaves untested is the thing `_describe`'s own docstring calls the
reason the selector is printed at all — that without it, four emissions read as
four streams one node produces at once rather than four a user picks between.
Assert the rendered form (`can emit (signal):`), which no other token in the
output spells.

The same file's `test_every_tool_on_the_shelf_prints_every_emission_it_declares`
claims totality in both directions in its docstring — "a name in the output that
no spec declares is the lie the field exists to make impossible" — and checks
only declared-to-output. `declared` is built and then used for nothing but a
non-emptiness assertion. Either check the reverse direction against the printed
names or stop claiming it.

Not gated on 05.6, but that item rewrites this command and this file; doing it
there rather than alone is fine, and doing it there without noticing is what
this item exists to prevent.
