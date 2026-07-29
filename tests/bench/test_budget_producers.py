"""Rule 4's other half: a ceiling nothing publishes is a number, not a budget.

The table defines what a limit is, but cannot say whether anything measures
against it — and four of twelve budgets do not, silently. A budget with no producer
cannot be missed, which is indistinguishable from compliance.

*Published* and *timed* are two different gaps and the second is wider: nine
of the twelve have no CI benchmark asserting a limit, so `TIMED` is pinned here
the same way. The prose that used to hold these counts got both of them wrong
(AUTO-GUARDRAILS §4 said "7 of the 11" and "2 of the 11"), which is the whole
argument for a set a test can read.

Checks, one per direction a key can go wrong:

- a budget in `BUDGETS` that no module under `src/` names, and is not declared
  in `WITHOUT_PRODUCER`;
- a module-level `*_BUDGET` constant whose value is not a budget key. Those
  constants exist because `pipeline/` sits below `bench/` and may not import it
  (ARCHITECTURE.md, layer diagram), so `preview.py` names its keys as string
  literals — reintroducing exactly the unchecked-key typo that `metrics.py`'s
  key registry exists to prevent. This closes it from the other end.

Neither check proves a key reaches `publish`. A textual reference is a weaker
claim than a call-graph trace and is the one worth making: it is stable against
how a module chooses to name its key, and the failure it catches — a ceiling
nobody wired up — does not need the stronger claim to be caught.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from sieve.bench.budgets import BUDGETS, TIMED, WITHOUT_PRODUCER

SRC = Path(__file__).resolve().parents[2] / "src" / "sieve"
BENCH_TESTS = Path(__file__).resolve().parent

#: `bench/` declares the keys; naming one there is not producing it.
_DECLARING_PACKAGE = SRC / "bench"


def _modules_outside_bench() -> list[Path]:
    return [path for path in SRC.rglob("*.py") if _DECLARING_PACKAGE not in path.parents]


@pytest.fixture(scope="module")
def referenced() -> set[str]:
    """Budget keys named by any module under `src/` outside `bench/`."""
    sources = [path.read_text(encoding="utf-8") for path in _modules_outside_bench()]
    return {key for key in BUDGETS if any(f'"{key}"' in text for text in sources)}


def test_every_budget_has_a_producer_or_is_declared_not_to(referenced: set[str]) -> None:
    unreferenced = set(BUDGETS) - referenced
    assert unreferenced == set(WITHOUT_PRODUCER), (
        "budgets with no producer must be declared in `budgets.WITHOUT_PRODUCER`; "
        f"undeclared: {sorted(unreferenced - WITHOUT_PRODUCER)}"
    )


def test_declared_producerless_budgets_have_not_quietly_grown_one(referenced: set[str]) -> None:
    """The list only shrinks, and shrinking it is a deliberate edit."""
    grown = WITHOUT_PRODUCER & referenced
    assert grown == set(), f"{sorted(grown)} now has a producer — remove it from `WITHOUT_PRODUCER`"


def test_without_producer_names_only_real_budgets() -> None:
    assert set(BUDGETS) >= WITHOUT_PRODUCER


def test_every_budget_constant_names_a_real_budget() -> None:
    """A `*_BUDGET = "..."` whose value is not a key is an unwatched metric."""
    offenders: list[str] = []
    for path in _modules_outside_bench():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
                continue
            value = node.value.value
            if not isinstance(value, str):
                continue
            for target in node.targets:
                named_budget = isinstance(target, ast.Name) and target.id.endswith("_BUDGET")
                if named_budget and value not in BUDGETS:
                    offenders.append(f"{path.name}:{ast.unparse(target)} = {value!r}")
    assert offenders == [], f"budget constants naming no budget: {offenders}"


#: `tests/bench/gate.py` is the single adjudicator, so a budget is timed in CI
#: if and only if some module here passes its key to `within_budget`. Matching
#: the call site rather than the key alone is what keeps this from counting the
#: meta-tests in this file, which name every key by construction.
TIMED_CALL = re.compile(r'within_budget\(\s*"([a-z_]+)"')


@pytest.fixture(scope="module")
def asserted() -> set[str]:
    """Budget keys some benchmark in `tests/bench/` judges against a limit."""
    keys: set[str] = set()
    for path in BENCH_TESTS.glob("test_*.py"):
        keys |= set(TIMED_CALL.findall(path.read_text(encoding="utf-8")))
    return keys


def test_timed_says_exactly_which_budgets_have_a_clock_on_them(asserted: set[str]) -> None:
    # Both directions, because both have been wrong. AUTO-GUARDRAILS §4 claimed
    # two timed budgets out of eleven while the table held twelve and three were
    # timed — a prose count nobody could check, which is what this replaces.
    assert asserted == set(TIMED), (
        "`budgets.TIMED` must name exactly the keys passed to `within_budget` in "
        f"tests/bench/; missing: {sorted(asserted - TIMED)}, "
        f"claimed but not asserted anywhere: {sorted(TIMED - asserted)}"
    )


def test_timed_names_only_real_budgets() -> None:
    assert set(BUDGETS) >= TIMED
