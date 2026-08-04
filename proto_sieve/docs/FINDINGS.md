# Findings

The spike's actual output. Three lists, appended as they happen.

## Prior proofs that had to be edited

*(A chunk forcing an edit to an earlier chunk's test is a leaked boundary.
Record which chunk, which test, and what it had to accommodate.)*

- **None through chunk 4.** Chunk 4 added the cache and `tests/test_render.py`
  was not touched: `render(node, bound)` kept its signature, callers do not
  create or pass caches, and no result changed. So materialization behaves as
  a secret, which is the answer the load-bearing chunk was asked for.
  **Caveat:** nothing is committed, so this is not verifiable from the tree —
  see `STATUS.md`.

## Halts

*(A chunk needed something a neighbour did not expose. Record what was needed,
from whom, and whether it turned out to be a missing interface item or a
leaked secret.)*

- **None yet.**

## Co-touches

*(Anticipated changes absorbed by two modules instead of one. Also: commits
touching the same pair of files repeatedly. Three or four on the same pair is
a signal; one is noise.)*

- **None yet.**

## Things learned that were not on any list

- **A result's address is `(recipe, input content)`, not the recipe alone.**
  The recipe hash addresses the *graph*; it says nothing about what was bound
  to its sources. A cache keyed on the recipe alone serves frame 0's answer for
  every frame after it. This is the same failure as two computations sharing
  one address, arriving one layer down, and it was not on the expensive list.
  Pinned by `tests/test_cache.py::test_a_different_input_is_a_different_result`.

- **Content-addressing costs a full input hash per call.** `_bound_digest`
  hashes every bound frame on every `render`. Correct, and for video obviously
  unaffordable — a real cost the design had not accounted for. The likely exit
  is that frames carry an identity from upstream (a decode-time digest, or a
  source-plus-index token) rather than being hashed at use. That is a decision,
  not an optimisation, and it belongs on the expensive list.

- **`Blur` and `Sharpen` have no implementation and that is deliberate.** They
  exist so identity has two ops with the same field shape to separate. Giving
  them behaviour would be scope the decomposition does not need proving.
