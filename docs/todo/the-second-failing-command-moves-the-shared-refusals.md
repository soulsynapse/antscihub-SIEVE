---
title: The second failing command moves the shared refusals
priority: normal
phase: 6
status: open
gated_on: nothing
opened: 2026-08-07
---

# The second failing command moves the shared refusals

`cli/run_cmd.py` holds `refuse`, `load_project`, `parse_span`, `span_for` and
`frame_source`, and its own docstring says why they are not yet in a
`cli/common.py`: v2 had one because two commands refusing in two spellings
would be two spellings of every error message a user sees, and until 06.2 there
was one speller. `preview` is the second, and it imports all five out of
`run_cmd` — so the trigger that docstring names has fired, and what stands in
the tree is a command importing another command for its error vocabulary.

The move is mechanical and the reason it is a separate item is the porting
discipline: 06.2 named two files and adding a third would have been a decision
riding along with a port. What the move has to preserve is the property the
sharing exists for — one spelling per refusal — so the item is done when both
commands import from `cli/common.py` and neither imports the other.

v2's `cli/common.py` is the shape to read, not to copy: it carries a
`FrameSourceContext`, a `WORKERS_OPTION` and a `lower_source_contract` that
have no referent here (`adr/no-kernel-apparatus.md`, and `PLAN.md` on lowering).
