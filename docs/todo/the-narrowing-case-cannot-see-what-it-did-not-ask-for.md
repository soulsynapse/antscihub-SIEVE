---
title: The narrowing case cannot see what it did not ask for
priority: normal
phase: 8
status: open
gated_on: nothing
opened: 2026-08-07
---

# The narrowing case cannot see what it did not ask for

`test_naming_a_tool_narrows_the_shelf_rather_than_resolving_a_version` in
`tests/unit/test_cli_inspect.py` passes when the narrowing is deleted from
`inspect_tools` — measured, with the mutant, in
`docs/findings/loop/2026.08.07-the-narrowing-case-is-the-only-one-that-survives-the-removal-of-the-narrowing.md`.
Both its assertions are keyed on the tool it asked about, and that tool is
present under either behaviour, so the nine other blocks that leak in are
invisible to it. Three cases named for other declarations kill the mutant
instead, by tripping `_one`.

The repair is to assert against the listing as a whole rather than the block
asked for: that `sieve inspect <id>` prints headline lines for that id and no
other, which is one line and fails the moment the narrowing stops narrowing.

The version half needs a decision rather than a patch. The case claims to check
that every registered version of an id is printed; all ten specs have one
version, so the count is `1 == 1`, and `_one`'s single-match assertion would
raise if any id ever had two — the helper cannot survive the condition the case
is named for. Either register a second version of some tool for the case to
stand on, or drop the version claim from the name and the docstring and let it
return when a second version exists. Registering one on the process-wide shelf
is what `test_a_tool_with_no_parameters...` already refuses to do for its own
fixture, so a locally built pair of specs passed to `_describe` is the likelier
shape.
