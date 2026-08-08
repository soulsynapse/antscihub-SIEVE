---
title: The dag propagation cases answer a mutation
priority: normal
phase: 3
status: done
gated_on: nothing
done_when: 'uv run python scripts/mutation_sweep.py --file src/sieve/pipeline/dag.py --mutant "upstream: ElementKind | None = resolved[parent] ==> upstream: ElementKind | None = ElementKind.PIXEL" --mutant "upstream_names = names[parent] ==> upstream_names = SOURCE_ELEMENT_NAMES" --mutant "indexed[node.node_id] = upstream and not spec.rate_changing ==> indexed[node.node_id] = not spec.rate_changing" --mutant "self.elements[node.node_id] is None ==> self.elements[node.node_id] is None and node.node_id == node_id" --mutant "if node.node_id in feeding and self.elements[node.node_id] is None ==> if self.elements[node.node_id] is None" --mutant "feeding.update(self.upstreams[node.node_id]) ==> pass" -- uv run pytest -q tests/unit/test_dag.py'
opened: 2026-08-07
---

# The dag propagation cases answer a mutation

The open question left by
[findings/loop/2026.08.07-a-declared-layout-and-an-isolation-test-both-pass-with-the-ancestry-dropped.md](../findings/loop/2026.08.07-a-declared-layout-and-an-isolation-test-both-pass-with-the-ancestry-dropped.md):
03.4's suite passed with `node_key`'s ancestry fold destroyed, because it
asserted only the direction that must not propagate. `dag.py` carries the same
shape of claim — meaning carries forward through preserving nodes, a rate change
unindexes everything after it, the earliest loss wins — and its cases were read
for coverage, never probed.

Reading the names says nothing either way: `a_branch_that_does_not_feed_the_asker
_is_not_blamed` is the negative and `meaning_carries_through_every_preserving
_node_after_a_redefinition` looks like its complement, which is exactly the
arrangement 03.4 also appeared to have. What settles it is the mutation, run
within the declared shape rather than by deleting a field: make the forward walk
stop one node early, make the loss attach to the node that asked rather than the
node that lost it, and see whether anything goes red.

Done when each propagating claim in `dag.py` has a mutation recorded against it
— the surviving ones repaired with a case, the rest noted as already covered so
the next reader does not re-run the probe.

## The probe was run and nothing survived, so this closes with the record

Six mutants, one per propagating claim the body names, each within the declared
shape rather than a deleted field. The forward element fold reading `PIXEL`
instead of its parent, and the names fold reading `SOURCE_ELEMENT_NAMES`
instead: the two ways "meaning carries forward through preserving nodes" could
be false. `_source_indexed` dropping the `upstream and` conjunction: a rate
change that unindexes itself and nothing after it. And three over
`element_lost_at`, which is where "the earliest loss wins" lives — the answer
forced to the node that asked rather than the node that lost it, the `feeding`
test dropped so a branch that feeds nobody is blamed, and the upstream
membership walk stopped so the set never grows past the asker.

```
$ uv run python scripts/mutation_sweep.py --file src/sieve/pipeline/dag.py \
    --mutant "upstream: ElementKind | None = resolved[parent] ==> upstream: ElementKind | None = ElementKind.PIXEL" \
    --mutant "upstream_names = names[parent] ==> upstream_names = SOURCE_ELEMENT_NAMES" \
    --mutant "indexed[node.node_id] = upstream and not spec.rate_changing ==> indexed[node.node_id] = not spec.rate_changing" \
    --mutant "self.elements[node.node_id] is None ==> self.elements[node.node_id] is None and node.node_id == node_id" \
    --mutant "if node.node_id in feeding and self.elements[node.node_id] is None ==> if self.elements[node.node_id] is None" \
    --mutant "feeding.update(self.upstreams[node.node_id]) ==> pass" \
    -- uv run pytest -q tests/unit/test_dag.py
KILLED    upstream: ElementKind | None = resolved[parent]
KILLED    upstream_names = names[parent]
KILLED    indexed[node.node_id] = upstream and not spec.rate_changing
KILLED    self.elements[node.node_id] is None
KILLED    if node.node_id in feeding and self.elements[node.node_id...
KILLED    feeding.update(self.upstreams[node.node_id])
mutation_sweep: 6 killed, 0 survived
```

So `test_dag.py`'s arrangement is not 03.4's: the negative case
(`a_branch_that_does_not_feed_the_asker_is_not_blamed`) and its apparent
complement do in fact pin opposite directions, and the pair that looked alike
from the names is not alike under the probe. Nothing was repaired because
nothing needed it, and the criterion above is the record — a later edit that
loosens one of these six goes red rather than quiet.

Closed by the `specify` run that wrote the criterion, which is the one case
where writing it and finding it green is the answer rather than the wrong
question: the item's whole subject was whether the probe kills, and running it
is what specifying it costs.
