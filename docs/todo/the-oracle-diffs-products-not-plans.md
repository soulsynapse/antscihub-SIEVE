---
title: The oracle diffs products, not plans
step: "05.8"
status: done
gated_on: nothing
done_when: "uv run pytest tests/integration/test_v2_oracle.py -q"
opened: 2026-08-07
---

# The oracle diffs products, not plans

Phase 5's gate made a test: the same pipeline built by hand in both repos,
both CLIs run on the stirred clip (05.5), outputs compared at the product
level. The frozen identity values (`adr/tools-not-filters.md`) are what make
"the same pipeline" mechanical rather than a judgement call. The resolved
plan is never compared — v3 re-derived the schema and the node graph on
purpose, so a plan-level diff would be a test that v3 failed to do what it
set out to do.

CI has no sibling worktree, so the v2 side is a checked-in artifact under
`tests/goldens/`, minted by 03.7's mechanism and carrying the exact
`git -C ../antscihub-SIEVE-v2` command that regenerates it. What runs in CI
is v3 against that artifact. A skip when the worktree is absent is the
failure mode this repo already has an item about
(`a-missing-encoder-skips-the-fixture-and-the-gate-stays-green.md`) and is
not available here.

The pipeline is more than one tool deep, or the oracle proves only that a
single kernel matches — which 03.7 and the Phase 4 items already prove one at
a time. What is new here is composition: window arithmetic across stages,
which is where v2's trailing-only contract failed and where v3's two-sided
window (01.3) is a claim nothing has tested end to end.
