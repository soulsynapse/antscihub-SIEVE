---
title: The second failing command moves the shared refusals
priority: normal
phase: 8
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

## The two commands already refuse an invalid parameter in two spellings

Folded in 2026-08-08, from the run that made `ExecutionPlan.build` wrap its own
validation in `InvalidParamsError` (`the-named-params-refusal-is-pre-empted-by-
its-only-caller.md`). Two consequences land on this item rather than that one,
because both are about who spells a refusal and where:

- `run_cmd` catches `GraphError` around `Dag.build` and nothing at all around
  `ExecutionPlan.build`, so a project whose parameters the tool refuses is a
  traceback from `sieve run` and a one-line refusal from `sieve preview` — the
  two spellings this item exists to end, over an error that now names the node
  and so is worth printing. It was a traceback before the wrap too; what
  changed is that there is now a sentence worth showing.
  **Corrected 2026-08-08 (review of f6508d7):** the first sentence no longer
  describes the tree. `run_cmd` now wraps the `ExecutionPlan.build`
  comprehension in `except ValueError`, and `GraphError` is a `ValueError`, so
  `InvalidParamsError` reaches a user as a one-line refusal from both commands
  and the two spellings this bullet named have converged. What is left of the
  bullet for the `cli/common.py` move is the *breadth*: the catch is stated in
  its own comment as being for a span the plan cannot answer for, while it in
  fact swallows every `ValueError` raised anywhere under `build` — so a
  programming error inside the plan walk now exits 1 with a bare `str(error)`
  and reads as a deliberate refusal. One spelling per refusal is the property
  the move preserves, and a catch that cannot tell a refusal from a defect is
  the one place that property costs something.
- `ValidationError` in `preview_cmd._render`'s except tuple no longer catches
  anything: the plan was the one thing under `render_*` that raised a raw one,
  and it now raises a `GraphError` already in the list. `_render`'s docstring
  and `tests/integration/test_cli_preview.py::
  test_a_value_the_tool_refuses_is_a_refusal_and_not_a_traceback` both explain
  the refusal by that entry, so the two say the list is load-bearing where the
  tree says it is not. Deleting the entry and re-pointing both sentences at
  `GraphError` is the edit; the test's assertion — exit 1, the field named —
  holds either way, which is why it stayed green through the wrap.
