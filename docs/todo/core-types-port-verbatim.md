---
title: core/types.py ports verbatim
step: "01.1"
status: open
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

## The port exists, on `scratch/core-types-port` (e515bf7)

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

It is on the scratch branch because it collided with the old
`ANNOTATION_LIMIT = 72`. That collision is settled —
`adr/annotation-limit-is-the-source-line-budget.md` derives the limit from the
source line's own budget (97) and binds the annotation rules at edit time, not
at the moment of port — so the port relands unmodified: `git checkout
scratch/core-types-port -- src/sieve/core/types.py tests/unit pyproject.toml`,
plus the `uv.lock` the numpy promotion regenerates. Diff against the v2 blobs
before claiming done, same as any port; the docstring's 76-character first
line is now in bounds and no line of the port may change on the way over.
