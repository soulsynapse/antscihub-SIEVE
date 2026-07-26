"""Observation: latency budgets and metric collection.

No Qt here. Headless and CLI runs have to be able to observe the same numbers
the GUI shows, otherwise "CLI and HPC parity" is aspirational.
"""

from sieve.bench.budgets import BUDGETS, Budget, BudgetMissError, Regime, check

__all__ = ["BUDGETS", "Budget", "BudgetMissError", "Regime", "check"]
