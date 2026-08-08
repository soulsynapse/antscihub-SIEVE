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

## 06.3's headless claim now rests on collection order (2026-08-08, from 07.4)

`tests/bench/test_loop_budget.py::test_the_measurement_ran_with_no_qt_in_the_process`
reads `sys.modules` at assertion time, which was the whole of the claim while
nothing in the tree imported Qt. 07.4 gave the tree a `tests/gui/`, and pytest
imports every test module during collection — before the first test runs — so
one top-level `from sieve.gui.app import ...` makes Qt resident for the entire
session and that assertion goes red no matter which directory it sits in.

07.4 held the claim exactly as written by keeping `tests/gui/` free of
module-scope Qt imports (the rule, with the reason, is in
`tests/gui/conftest.py`): collection stays Qt-free and `tests/bench` runs
before `tests/gui` in the order pytest walks `testpaths`. That is discipline
plus an ordering, not a mechanism, and this item is where both stop being
tenable — it measures the same keys *through* the GUI, in a session where a
`QApplication` exists by construction. So the residency assertion has to be
restated here rather than carried: what the headless numbers need is that
*they* were taken with no Qt loaded, which is a claim about one measurement's
process and not about the suite's. Whether that means a subprocess, a separate
invocation, or retiring the runtime check in favour of `headless`'s static
guarantee is this item's to decide.
