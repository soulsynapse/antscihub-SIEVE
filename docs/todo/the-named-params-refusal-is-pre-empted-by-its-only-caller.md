---
title: The named params refusal is pre-empted by its only caller
priority: normal
phase: 3
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_plan.py -q -k invalid_params_names_the_node"
opened: 2026-08-08
---

# The named params refusal is pre-empted by its only caller

`dag.InvalidParamsError` exists so that a node whose resolved parameters are
invalid is reported *by node id* — pydantic's own message carries the field and
the model and not the node, and the reader it is written for is the interactive
loop, where a field name with no owner is a hunt through the graph. `Dag.
node_keys` raises it. Nothing in the tree ever sees it.

`ExecutionPlan.build` is the only caller of `node_keys` in `src/`. It builds its
`params` dict — `spec.params_model.model_validate(resolved_params(node,
replicate))` for every node in `dag.order` — before the `cls(...)` call whose
`keys=` argument reaches the walk, and the walk iterates that same `dag.order`.
So the raw `ValidationError` from the plan's own dict is what escapes, one
validation earlier, on the identical call over the identical node set:

    ExecutionPlan.build(dag, source=..., span=...)
    # pydantic ValidationError: 1 validation error for BlurParams / radius

Both CLI surfaces confirm what that costs. `run_cmd.load_project` and
`preview_cmd._render` both catch `ValidationError` and print it as the user's
answer, so the message a user gets for a bad parameter names `BlurParams` and
`radius` and no node — which is the exact sentence
`a-declared-validationerror-names-the-node-it-refused.md` was minted to end.

Done when the plan's path raises something naming the node, so the named
refusal has a reader. The two obvious shapes are that `ExecutionPlan.build`
wrap its own validation the same way, or that the two validations become one
site — which of those is the work's call, and the criterion names neither, only
that a plan built over a node with invalid parameters names that node.

Not in scope: making either path survive an invalid node. The refusal stays a
refusal for the reason the originating item gives — invalid parameters are a
document that cannot run, and swallowing them per node hands the executor a
graph it fails on later and further away.
