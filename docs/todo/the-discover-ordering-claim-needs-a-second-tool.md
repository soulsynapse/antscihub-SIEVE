---
title: discover()'s ordering claim is untested until a second tool lands
status: open
priority: normal
phase: "03"
gated_on: a second module in sieve/tools/
opened: 2026-08-07
---

# discover()'s ordering claim is untested until a second tool lands

`sieve/tools/__init__.py` documents that `discover()` returns specs ordered by
`(tool_id, version)`, and replacing `sorted(REGISTRY, key=...)` with bare
`tuple(REGISTRY)` leaves the whole suite green — `downsample` is the only tool
on the shelf, so sorted and unsorted are the same tuple. Measured at 03.7.1 and
recorded in
`docs/findings/loop/2026.08.07-a-fresh-interpreter-is-where-the-fixture-and-the-subject-come-apart.md`.

The gap is absent-subject rather than untested-behaviour, and faking a second
spec into the process-wide `REGISTRY` would prove the fake. So this waits for a
real second tool. Whoever adds one should assert in
`tests/unit/test_tool_discovery.py` that the pair comes back in
`(tool_id, version)` order and not in `pkgutil` order — the two differ only
when the module filenames sort differently from the tool ids, so the test is
worth nothing unless the second tool is one where they do, or unless the
assertion is written against ids rather than against a hardcoded pair.

It is here because the finding says nothing in the tree will prompt it: the
mutant is silent, the docstring reads as settled, and the next tool arrives
under an item about that tool.
