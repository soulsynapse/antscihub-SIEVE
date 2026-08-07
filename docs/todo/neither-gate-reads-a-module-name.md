---
title: Neither gate reads a module name
status: open
priority: low
phase: 1
gated_on: nothing
opened: 2026-08-07
---

# Neither gate reads a module name

`dead_language` in `scripts/doc_index.py` passes a word fused into a path
because "`filter_base.py` is a name, not language", and its docstring hands
that half to "the Phase-1 spelling gate". 01.5 built that gate, and it reads
the *contents* of every `src/sieve/**/*.py` as text — never the path it read
them from. So the hand-off drops the case both docstrings name: a module
called `src/sieve/core/filter_base.py` trips neither checker.

The hole is narrow, which is why this is an aside rather than a defect in
01.5. Any module that is imported is spelled inside some other module's
`from` line, and the text scan catches it there; only a module nothing
references escapes. But the pair is documented as covering the rename
between them, and it does not.

The fix is one line in `_hits` — yield on the relative path as well as on
each line — plus deciding what a hit's line number is when the path is what
offended. Or the two docstrings stop claiming the pair is exhaustive and say
that names are checked by review. Either settles it; the current state reads
as covered and is not.
