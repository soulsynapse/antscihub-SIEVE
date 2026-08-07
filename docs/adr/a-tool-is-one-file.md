---
title: A new tool is one file
adr: 7
position: "01.03"
status: settled
decided: 2026-08-06
---

Adding a tool touches exactly one module in `sieve.tools` — spec, params,
`run` — and nothing else; a tool that needs a second file edited is an
architecture failure to stop and fix, not route around.

Why: v2's non-GUI half roughly held this bar and its GUI half is the
counterexample — `gui/filter_tab.py`, 2,321 lines holding eleven jobs, a toll
every v2 filter paid. The stop-and-fix clause is v2.5's
(`docs/archive/DESIGN-SESSION.md`, the rebuilt Exchange-5 design): route
around the failure once and the one-file property is gone for every tool
after. The licensed exception is declaring a new *kind* — a presentation
stereotype, a window shape — which is a contract change and edits the
contract's consumers by design
([gui-knows-kinds-not-tools](gui-knows-kinds-not-tools.md),
[no-kernel-apparatus](no-kernel-apparatus.md)).
