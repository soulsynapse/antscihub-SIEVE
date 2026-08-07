---
title: The graph ports verbatim; the plan renames
step: "02.2"
status: deferred
gated_on: "a ruling on three: whether the backend field leaves the cache key
  (dropping `backend/` moves every node key, which this item calls a blocker),
  where `core/replicates.py` lands, and whether Phase 2's graph can precede the
  schema it is written against"
done_when: "uv run pytest tests/unit/test_dag.py tests/unit/test_cache_key.py tests/unit/test_plan.py -q"
opened: 2026-08-06
---

# The graph ports verbatim; the plan renames

`pipeline/dag.py` and `cache_key.py` verbatim; `plan.py` port-with-rename
(PLAN.md, porting discipline). The cache-key test ports unchanged — the
identity values are frozen (`adr/tools-not-filters.md`), so what enters a key
means the same thing it meant in v2. A key that changes for any reason other
than the field rename itself is a stop-and-write blocker, not a constant to
update.

## Deferred 2026-08-07: the three modules do not import, three ways

Read at v2 `main` (671aa8a). Every name each module imports was checked
against what `src/sieve/` holds after 01.5. The tool contract side is clean —
`dag.py`'s eight `filter_base` names, `plan.py`'s three, and `cache_key.py`'s
`FilterSpec`/`Mode` all exist in `core/tool_base.py`, `StreamSpec` included,
and `REGISTRY`/`FilterRegistry`/`UnknownFilterError` are `tool_registry.py`'s
three under ADR-1's spellings. What is missing is not the contract.

**The backend field cannot be renamed away, and its removal is the blocker
this item names.** `cache_key.node_key` folds `backend_identity(backend)` into
every node digest, dropping out only where the spec claimed
`backend_agnostic`. PLAN.md drops `backend/` outright, and 01.2 cut
`backend_agnostic` by name (`tool_base.py:51`). So the sixth position of every
`_digest("node", ...)` is either a field v3 has no way to compute or a hole —
and a hole moves every key in the graph. That is not the field rename; it is
this item's own stop-and-write sentence, arriving on the port rather than on a
later edit. `Backend` is also a parameter of `Dag.build`, `ExecutionPlan`, and
17 / 7 / 3 references across the three test files, so it is a signature
question and not only a digest one.

**`core/replicates.py` is named nowhere in PLAN.md's port disposition.** All
three modules take `replicate: Replicate | None`, and `resolved_params(node,
replicate)` is what makes the key canonical per replicate rather than per
node — `cache_key.py`'s own docstring argues the signature. The file is not
listed verbatim, port-with-rename, re-derived, or dropped; carrying it is the
"no files beyond what the item names" refusal, and re-deriving it is 03.1's
work, since `adr/detector-is-a-node.md` already rules on `Replicate.roi`.

**Phase 2's graph is written against Phase 3's schema.** `dag.py` imports
`Node`/`Pipeline`, `cache_key.py` `Node`/`resolved_params`, `plan.py`
`ClipRange`/`Node`/`resolved_params`; the tests add `Edge`, `Project`, and
`SourceRef`. `pipeline_model.py` is Phase 3, re-derived, and
`adr/v2-does-not-import.md` forbids any module spelling a v2 field name — so a
stopgap `Node` to unblock 02.2 either spells them, which the ADR refuses, or
diverges from what the ported modules read, which is not verbatim. The three
test files build 48 `Pipeline(...)` and 73 `Node(...)` literals between them;
none survives a schema re-derivation untouched, and `test_plan.py` additionally
imports `CostEstimate`, which 01.2 cut. All 56 cases fail at import, not at
assertion. `decode.lowered.LoweredPrefix` (all three modules) and
`decode.identity.decoder_identity` (`cache_key.py`) are the same shape one
item earlier — 02.1, deferred.

Nothing was written to `src/` or `tests/`. The measurement outlasting this
item is `findings/2026.08.07-v2s-pipeline-does-not-separate-from-its-schema.md`;
`findings/loop/2026.08.07-a-criterion-drafted-from-v2s-file-list-names-a-subject-two-phases-out.md`
is the near neighbour and not the same fault — the criterion here names the
right three test files for the right three modules, and it is the modules that
cannot land.
