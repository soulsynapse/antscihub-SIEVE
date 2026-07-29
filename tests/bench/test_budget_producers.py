


























from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from sieve.bench.budgets import BUDGETS, TIMED, WITHOUT_PRODUCER

SRC = Path(__file__).resolve().parents[2] / "src" / "sieve"
BENCH_TESTS = Path(__file__).resolve().parent


_DECLARING_PACKAGE = SRC / "bench"


def _modules_outside_bench() -> list[Path]:
    return [path for path in SRC.rglob("*.py") if _DECLARING_PACKAGE not in path.parents]


@pytest.fixture(scope="module")
def referenced() -> set[str]:

    sources = [path.read_text(encoding="utf-8") for path in _modules_outside_bench()]
    return {key for key in BUDGETS if any(f'"{key}"' in text for text in sources)}


def test_every_budget_has_a_producer_or_is_declared_not_to(referenced: set[str]) -> None:
    unreferenced = set(BUDGETS) - referenced
    assert unreferenced == set(WITHOUT_PRODUCER), (
        "budgets with no producer must be declared in `budgets.WITHOUT_PRODUCER`; "
        f"undeclared: {sorted(unreferenced - WITHOUT_PRODUCER)}"
    )


def test_declared_producerless_budgets_have_not_quietly_grown_one(referenced: set[str]) -> None:

    grown = WITHOUT_PRODUCER & referenced
    assert grown == set(), f"{sorted(grown)} now has a producer — remove it from `WITHOUT_PRODUCER`"


def test_without_producer_names_only_real_budgets() -> None:
    assert set(BUDGETS) >= WITHOUT_PRODUCER


def test_every_budget_constant_names_a_real_budget() -> None:

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






TIMED_CALL = re.compile(r'within_budget\(\s*"([a-z_]+)"')


@pytest.fixture(scope="module")
def asserted() -> set[str]:

    keys: set[str] = set()
    for path in BENCH_TESTS.glob("test_*.py"):
        keys |= set(TIMED_CALL.findall(path.read_text(encoding="utf-8")))
    return keys


def test_timed_says_exactly_which_budgets_have_a_clock_on_them(asserted: set[str]) -> None:


    assert asserted == set(TIMED), (
        "`budgets.TIMED` must name exactly the keys passed to `within_budget` in "
        f"tests/bench/; missing: {sorted(asserted - TIMED)}, "
        f"claimed but not asserted anywhere: {sorted(TIMED - asserted)}"
    )


def test_timed_names_only_real_budgets() -> None:
    assert set(BUDGETS) >= TIMED
