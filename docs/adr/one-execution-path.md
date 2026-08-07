---
title: One execution path
adr: 10
position: "04.01"
status: settled
decided: 2026-08-06
---

Preview and production are one executor over one plan; a preview is the same
pipeline with a span or resolution cut prepended, so what the user tuned
against cannot diverge from what the run produces.

Why: build batch-first and scrubbing arrives later as a second, subtly
different render path, and "the preview looked fine" becomes a support burden
(`docs/archive/DESIGN-SESSION.md`, Exchange 4). v2 held this rule; CLAUDE.md
lists it as implied by the components but not adopted — this adopts it. The
bench gate depends on it: budgets measured headless through the preview
session (PLAN.md, Phase 6) only bind the GUI if the GUI runs the same path.
