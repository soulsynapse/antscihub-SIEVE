---
title: discover()'s ordering claim is untested until a second tool lands
status: open
priority: normal
phase: "03"
gated_on: nothing
opened: 2026-08-07
---

# discover()'s ordering claim is untested until a second tool lands

`sieve/tools/__init__.py` documents that `discover()` returns specs ordered by
`(tool_id, version)`, and replacing `sorted(REGISTRY, key=...)` with bare
`tuple(REGISTRY)` leaves the whole suite green — `downsample` was the only tool
on the shelf, so sorted and unsorted were the same tuple. Measured at 03.7.1 and
recorded in
`docs/findings/loop/2026.08.07-a-fresh-interpreter-is-where-the-fixture-and-the-subject-come-apart.md`.

Phase 4 landed the rest of the shelf, so the absent subject this waited for is
here. What the tools did not bring is a *disagreement*: every tool_id is
spelled exactly like the module that registers it, `pkgutil.iter_modules` walks
the package in filename order, and `REGISTRY` keeps insertion order — so
scan order and `(tool_id, version)` order are the same tuple for ten tools the
way they were for one, and the mutant is still silent. Ten tools whose ids
match their filenames is not one counterexample.

So the test has to construct the disagreement rather than find it, and the
docstring already says how without calling it that: `discover()` returns the
shelf and not the scan's own results, so a spec registered after the scan by
something else is in the answer. One registered with an id that sorts before
the first module's comes back first if the sort is real and last if it is not.
That is not the fake this item refused at 03.7.1 — the refusal was standing a
fake spec in for the missing *shelf*, and the shelf is now ten real tools with
the ordering claim made over them.

It is here because the finding says nothing in the tree will prompt it: the
mutant is silent, the docstring reads as settled, and the next tool arrives
under an item about that tool — and a tool that would break the tie by itself
is one whose id disagrees with its filename, which `adr/a-tool-is-one-file.md`
gives nobody a reason to write.
