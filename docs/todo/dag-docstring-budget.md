---
title: dag.py docstring budget
status: open
priority: unassessed
gated_on: >
  nothing structurally — a Kendrick decision on whether the docstring
  convention's per-symbol ban and 400-word prose cap should exempt this file,
  or fold it into CONTRACT_MODULES alongside cache_key.py, the module it says
  it completes
reads: [src/sieve/pipeline/dag.py, tools/docstring_audit.py]
---

# dag.py docstring budget

`pipeline/dag.py` was picked by `tools/docstring_audit.py --next` for the
docstring-convention sweep (module docstring stating the file's one secret;
no class/function docstrings elsewhere; 250/400-word caps). It is flagged
rather than brought to the convention.

**The secret is genuinely one.** The module docstring already states it:
`Dag.build` resolves a `Pipeline` against a `FilterRegistry` into an ordered,
type-checked graph — or raises exactly why it cannot — so the executor, the
cache key, and any other consumer that needs a run order takes it from here
rather than re-deriving one. Every class and method serves that one
resolve-order-validate role: the four error types are the four ways a
`Pipeline` can fail to become a `Dag`, and `elements`/`source_indexed`/
`needs_chroma`/`node_keys` are folds over the same topological order the
constructor already computed, not separate responsibilities. It does not fit
the flag path's clause (a).

**What does not fit is the budget.** `tools/docstring_audit.py`'s own
measurement: 367-word module docstring, already over the 250 cap on its own;
22 symbol docstrings totaling 2,686 words; 461 words of comments; 3,147 words
of prose total against the 400-word cap — over by roughly 8x. They are not
restatements of signature or control flow; they are one-off reasons specific
to one method: why the five rejections fire in the stated order (an
unresolved filter before a cycle, because a graph half of whose nodes name
nothing has no meaningful cycle to describe; a cycle before port wiring,
because ordering the later checks needs the sort the cycle check produces);
why `_topological` drains the ready set in declaration order rather than
insertion order (so the executor's schedule and a cost report stay
comparable across runs of one unchanged document); why `node_keys` folds
`NotCacheableError` per-node instead of letting it propagate out of the walk
(one non-deterministic node in a twelve-node graph should not cost the cache
entries of the eleven that are fine); why `_check_edges` walks in topological
order even though an edge check is local (so the earliest mismatch in a
graph with several is the one reported, letting a user fix a chain from the
top); the corrected note on `node_keys`' `backend` argument recording that it
used to be a single `Backend` and why that was wrong. Each is local to its
one method, underivable from the code, and has no other natural owner — not
a measurement (`docs/findings/`), not an architecture rule
(`docs/ARCHITECTURE.md` or a PAR-style rationale) so much as the specific
reason one method's behaviour is shaped the way it is. Folding 22 of these
into one 250-word module docstring would not compress them, it would delete
them — clause (c) of the flag path: "the prose is load-bearing in a way the
budget would destroy... it records why the code is the shape it is in a way
the code cannot."

**No split is proposed.** Every method reads the same `order`/`upstreams`/
`downstreams`/`ports`/`specs` the constructor derives, and the four folds
(`elements`, `source_indexed`, `needs_chroma`, `node_keys`) each depend on
that same topological order rather than on each other — there is no seam
where two of them could become a second file without both still needing the
first file's `Dag.build` output. The co-change check CLAUDE.md prescribes was
not run because there is no candidate second file to check it against.

**What this item is asking Kendrick to decide**, one of:
1. Add `pipeline/dag.py` to `CONTRACT_MODULES` in `tools/docstring_audit.py`
   (600/900-word caps, per-symbol docstrings allowed). The module docstring
   already frames this file as `cache_key.py`'s missing half — "the traversal
   `cache_key.py` computes one node's key... and declines to say which nodes
   those are; `node_keys` below is the traversal that answers it" — which is
   the same load-bearing-prose argument that put `cache_key.py` on the
   contract list in the first place.
2. Accept the loss and force the file to the convention anyway, moving what
   survives triage into the module docstring and accepting the rest (the
   per-method ordering and cache-fold rationale) is deleted rather than
   relocated, since nothing else in the doc tree owns per-method
   implementation rationale at this grain.
3. Leave it flagged permanently, the same as `filter_tab.py`.

No code or docstring in `dag.py` was changed by this pass.
