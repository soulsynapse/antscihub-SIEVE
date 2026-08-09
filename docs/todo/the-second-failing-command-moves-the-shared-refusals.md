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

## The docstring this item quotes is gone, and the third caller spells one option two ways

Folded 2026-08-09, from the review of 08.4 (`753c241`), which added
`cli/materialize_cmd.py` as the third importer of `run_cmd`'s vocabulary. Two
things move on this item and neither is a defect in that commit:

- The paragraph this item quotes no longer exists. `run_cmd.py` said "the second
  command that can fail is what moves these", which had already fired and not
  moved them; 08.4 rewrote it to say they stay in `run_cmd` and the other
  commands import them, and named a different trigger — a fourth caller, or a
  refusal that has nothing to do with running a graph. So the item's premise
  ("the trigger that docstring names has fired") now cites a sentence the tree
  does not hold, and the tree states a counter-argument to the move rather than
  an argument for it. This item is where that is settled either way; the note is
  so a later session does not read the new paragraph as the decision.
- The same commit is the counter-example to the new paragraph's own claim.
  `materialize_cmd` imports `refuse`, `load_project`, `span_for` and
  `footage_end`, and then writes its own `_target` for the replicate lookup:
  `--replicate` on `sieve materialize` takes an id *or* a name, while
  `--replicate` on `sieve preview` takes an id only (`preview_cmd._target`,
  around `Project.replicate`). One option, two commands, two meanings and two
  refusal messages — the property "one spelling per refusal" that this item
  exists to preserve is already not held, and it is the argument's own subject
  rather than a style point. Whichever way the `cli/common.py` question is
  settled, the replicate lookup is one of the things that has to end up in one
  place. `Project.replicate` is the model's own lookup and neither command's
  name branch goes through it.

## The trigger the new paragraph named has now fired, on both of its clauses

Folded 2026-08-09, from 08.5 (`47bf42c`), which added `cli/sweep_cmd.py`.
`run_cmd.py`'s rewritten paragraph names two triggers for the move — a fourth
caller, or a refusal that has nothing to do with running a graph — and
`sweep_cmd` is both at once. It imports `refuse` and nothing else from
`run_cmd`, because it opens no project, builds no plan and runs no graph: what
it refuses is an unparseable `--workers` list, a design with no cell in it, and
a platform that will not pin a process. So the argument for leaving the
vocabulary in `run_cmd` — that its callers are all running graphs and the
module they import from is the one that does it — no longer describes the tree,
and a bench command reaching into the run command for the word "refuse" is the
shape this item exists to end.

Nothing was moved by 08.5, deliberately: that item named two files, and adding
a third would be the decision-riding-along-with-a-port its own second paragraph
refuses.

## 2026-08-09: the run-start refusals are multi-line, and only their first line is labelled

Folded from the review of `a50027a`, which added `run_cmd._external_inputs` and
with it the first refusals this command builds by joining several complaints
into one message. `resolve_source.source_files` raises with one line per absent
source root; `_external_inputs` catches that and prefixes `_label(target)` —
which lands on the first line only, so a fan-out where two replicates each miss
two files prints four node lines under two replicate names, and lines two and
four say nothing about whose they are. `Project.check_input_hashes` has the same
shape one level down, naming every changed node in one string.

It is a small defect and it is precisely against the promise these refusals are
built to make — a reviewer with several unmounted inputs learns about all of
them *and which run wants which*. It goes here rather than in its own item
because the fix is a spelling decision about how this command composes a
multi-part refusal, which is the vocabulary this item moves: whatever
`cli/common.py` ends up holding, one function that labels every line of a
collected refusal is the natural member, and solving it in `run_cmd` first would
be the second spelling to reconcile.

This item has no `done_when`, so nothing was widened.
