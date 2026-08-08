---
title: The first cut meets its gate — parity, both regimes, the list still empty
step: "07.11"
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui/test_gui_cli_parity.py -q && uv run pytest tests/bench/test_gui_loop_budget.py -q"
opened: 2026-08-08
---

# The first cut meets its gate — parity, both regimes, the list still empty

Phase 7's gate as a step, so closing the phase is work a review checks rather
than a sentence in PLAN.md. Three claims:

GUI/CLI parity at the executor level on the stirred clip — the fixture left
the GUI test in 05.5 precisely so the oracle could run first, and now the GUI
answers to the same fixture from the other side.

Both budget regimes measured through the GUI, against the same
`bench/budgets.py` keys 06.3 measured headless — which is the attribution
Phase 6 existed to buy: a number that regresses here is the GUI's, and
nothing else's. Scoped to the keys whose producers this cut builds:
`density_rebuild` has none — the band-power density strip is a later cut,
since it drags band-power caching behind it — so it stays declared in
`budgets.WITHOUT_PRODUCER` rather than measured through a surface that does
not exist. A miss inside the scope is a defect or a declared debt in
`budgets.IN_DEBT` with the item that repays it, never a widened ceiling
(VISION.md's scope clause).

And the `gui-computes-nothing` exception list is as empty as Phase 0 left it,
now that there is a GUI for it to be empty about.
