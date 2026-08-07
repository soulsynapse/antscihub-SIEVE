---
title: Guidance is a spec field, not a file per tool
priority: normal
phase: 4
status: done
gated_on: nothing
opened: 2026-08-07
---

# Guidance is a spec field, not a file per tool

Ruled 2026-08-07, and neither of the two obvious answers won. There is no
per-tool `.md` in v3 — a second home for a fact drifts, which is what the
derived-docs machinery exists to prevent — and dropping guidance outright is
wrong too, because VISION's project pane has the user hitting a down expander
that shows "all the help text they need". That is a consumer, so the text is
a declaration.

It arrives as a `ToolSpec` field in Phase 7, with the expander that reads it
(`adr/declared-means-verified.md`). Until then it lives in the tool's module
docstring, which is already where this repo keeps a contract, and which is
written at the only moment anyone knows what the tool is for: while writing
it. Phase 7 promotes it.

What this closes for every Phase 4 item is the clause about the question
being open. A tool item creates no document and no field; it writes a
docstring, which it was doing anyway.
