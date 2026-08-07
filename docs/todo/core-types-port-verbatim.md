---
title: core/types.py ports verbatim
step: "01.1"
status: done
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

## Reviewed 2026-08-07: done

The three hashes above were recomputed from `HEAD`, not read back from this
file, and all three still equal v2's. Identity is the stronger claim than the
one the item set for itself — "a diff that shows anything but import lines is
the item failing" admits import-line drift, and there is none, so the file
carries `sieve.core.types` unrenamed as the body says. `e515bf7`'s blobs are
the same three, which is what "relanded unmodified" has to mean; the scratch
branch holds nothing `v3` lacks. The gate passes at 27, and the whole gate —
`ruff check && lint-imports && pytest` — is green at 5 contracts and 66 tests,
so the ported module does not owe v3's own lint or layering anything. The
scaffold annotation measures 76 against ADR-16's 97.

The message on 883ec97 is left wrong on purpose. Its diff is this port; its
subject and body describe ADR-16, which actually landed in 3cc9a99 — a
concurrent session committed a staged tree that was not its own. So
`git log -- src/sieve/core/types.py` answers with an ADR, and a search for the
ADR answers with two commits, one of which never touched it. That is a real
cost here specifically, because this repo deletes an item's text on completion
and names git as where it is recovered from. But the fix is a history rewrite,
and whether an unpushed branch's history is worth rewriting is Kendrick's call,
not a reviewer's. Raised rather than done: two commits from the tip, nothing
pushed, so it is cheap if he wants it. Until then this paragraph is the record
that the diff and the message disagree.
