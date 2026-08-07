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

It is on a scratch branch and not on `v3` for the reason below. Landing it is
`git checkout scratch/core-types-port -- src/sieve/core/types.py tests/unit
pyproject.toml` once the scaffold question is answered.

## Blocker — the criterion passes and the gate does not

`uv run pytest -q` is red on two `tests/docs/test_doc_index.py` cases, neither
about the port: `collect_modules` raises `types.py: docstring first line is 76
chars; the scaffold column holds 72`. The ported docstring opens *"Frame, ROI,
quantities, and metadata value objects shared across all layers."*

The refusal is not confined to SCAFFOLD.md. `scripts/doc_index.py` collects
modules before it writes anything, so one over-limit docstring stops the run
and `docs/todo/.index.md` and `docs/findings/.index.md` go stale too — this
item's own `awaiting-review` and the finding below could not reach their
indexes. That is why the port is not on `v3`: it would have to arrive with a
red gate *and* two derived files asserting a tree that no longer exists, and a
repo that lies is worse than an item that stopped.

Both rules in the collision are v3's, and both are load-bearing, so a worker
cannot pick one:

- Shortening the line satisfies `ANNOTATION_LIMIT` and breaks the sentence
  above that calls any non-import difference the item failing.
- Raising the limit, or taking the annotation from the docstring's first
  *sentence* rather than its first *line*, satisfies the port and changes
  `scripts/doc_index.py` — a decision about the scaffold rule, which is not
  this item's to make and which governs every port item after it.

`findings/2026.08.06-the-scaffold-annotation-does-not-fit-a-ported-module.md`
has the census that makes this a decision rather than a typo: 46 of v2's 124
module docstrings are over 72, five more open with a wrapped fragment that is
not a sentence, and 72 renders a 106-column tree line so it was never the
100-column budget's number. `decode-ports-verbatim.md`,
`the-graph-ports-verbatim-the-plan-renames.md` and
`the-tool-contract-ports-with-its-rename.md` hit the same wall.
