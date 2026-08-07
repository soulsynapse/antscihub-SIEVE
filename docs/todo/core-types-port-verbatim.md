---
title: core/types.py ports verbatim
step: "01.1"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/unit/test_types.py tests/unit/test_quantities.py -q"
opened: 2026-08-06
---

# core/types.py ports verbatim

The four dimensioned quantities and rational media time, byte-identical
modulo the import path (PLAN.md, porting discipline). `tests/unit/
test_types.py` and `test_quantities.py` port with it as the spec. Nothing is
cut and nothing is added: this file is the copy-verbatim anchor of `core`,
and a diff against `git -C ../antscihub-SIEVE-v2 show main:src/sieve/core/types.py`
that shows anything but import lines is the item failing.

## The port landed on `v3`, verbatim (883ec97)

`src/sieve/core/types.py`, `tests/unit/test_types.py` and
`tests/unit/test_quantities.py`, byte-identical to the v2 blobs — the import
path is `sieve.core.types` in v2 already, so verbatim needed no rename at all.
`numpy` promotes from the dev group into `dependencies` there: `types.py` types
the frame array it carries, so the shipped package imports numpy from its first
module. OpenCV stays dev-only until `decode` lands.

```
$ uv run pytest tests/unit/test_types.py tests/unit/test_quantities.py -q
...........................                                              [100%]
27 passed in 0.04s
```

It sat on a scratch branch only because it collided with the old
`ANNOTATION_LIMIT = 72`. That collision is settled by
`adr/annotation-limit-is-the-source-line-budget.md`, and the port relanded
unmodified — no line changed on the way over.

Verbatim is checked as blob identity rather than by reading a diff, because
this worktree stores CRLF and v2's blobs are LF, so a textual diff calls all
625 lines changed and proves nothing. `git rev-parse :<path>` against
`git -C ../antscihub-SIEVE-v2 rev-parse main:<path>` compares what git
normalized, and all three matched:

```
89cd4011668590f177e2083e502574d83476104e  src/sieve/core/types.py
24a985c4be129722d009f049efdba0aa66e021c5  tests/unit/test_types.py
95e95d0e0f6d5cebe6aae0bbb299b6ce3026982c  tests/unit/test_quantities.py
```

The scaffold now carries the module's 76-character annotation, in bounds
under the new limit — the first evidence that the derived-docs run survives a
real module.

Two things for the reviewer. The landing commit's message is the ADR's, not
the port's: a concurrent session committed this staged tree under its own
subject, and 883ec97's diff is the port while its message describes ADR-16.
And `scratch/core-types-port` (e515bf7) is now redundant.
