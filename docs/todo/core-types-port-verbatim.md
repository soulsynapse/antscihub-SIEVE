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
