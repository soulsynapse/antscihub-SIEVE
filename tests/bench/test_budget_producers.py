"""The table's other half: a ceiling nothing publishes is a number, not a budget.

`test_budget_table.py` pins the table against VISION.md, so the two cannot
disagree about what a limit *is*. Neither of them can say whether anything ever
measures against it, and ten of the twelve are still measured by nothing while
the table reads as twelve enforced ceilings. A budget with no producer cannot be
missed, which is indistinguishable from compliance.

*Published* and *timed* are two different gaps and the second is wider: a
published budget shows a session it was missed, a timed one catches the miss
before it ships. Both are declared as sets and both are checked in both
directions, so paying either down is a deletion here rather than a silently
truer tree — 06.2 deleted the preview session's two from `WITHOUT_PRODUCER`, and
`TIMED` is still empty until 06.3's benchmark puts a clock on them.

Checks, one per direction a key can go wrong:

- a budget in `BUDGETS` that no module under `src/` names, and is not declared
  in `WITHOUT_PRODUCER`;
- a module-level `*_BUDGET` constant whose value is not a budget key. Those
  constants exist because `pipeline/` sits below `bench/` and may not import it
  (`.importlinter`, layers), so a module below the line names its keys as string
  literals — reintroducing exactly the unchecked-key typo that `metrics.py`'s
  key registry exists to prevent. This closes it from the other end.

Neither check proves a key reaches `publish`. A textual reference is a weaker
claim than a call-graph trace and is the one worth making: it is stable against
how a module chooses to name its key, and the failure it catches — a ceiling
nobody wired up — does not need the stronger claim to be caught.

The two scanners are exercised against planted text as well as against the
tree, because a scanner that reached nothing would report the same emptiness the
tree nearly has: two produced keys and no timed ones is close enough to nothing
that a broken scanner still reads as green.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable
from pathlib import Path

import pytest

from sieve.bench.budgets import BUDGETS, TIMED, WITHOUT_PRODUCER

SRC = Path(__file__).resolve().parents[2] / "src" / "sieve"
BENCH_TESTS = Path(__file__).resolve().parent

#: `bench/` declares the keys; naming one there is not producing it.
_DECLARING_PACKAGE = SRC / "bench"


def _modules_outside_bench() -> list[Path]:
    return [path for path in SRC.rglob("*.py") if _DECLARING_PACKAGE not in path.parents]


def _keys_named_in(sources: Iterable[str]) -> set[str]:
    texts = list(sources)
    return {key for key in BUDGETS if any(f'"{key}"' in text for text in texts)}


@pytest.fixture(scope="module")
def referenced() -> set[str]:
    """Budget keys named by any module under `src/` outside `bench/`."""
    return _keys_named_in(path.read_text(encoding="utf-8") for path in _modules_outside_bench())


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


def test_the_walk_reaches_the_modules_that_exist() -> None:
    """A scanner over a tree it never opened cannot be told from a green one."""
    walked = {path.relative_to(SRC).as_posix() for path in _modules_outside_bench()}
    assert "pipeline/executor.py" in walked
    assert "cli/run_cmd.py" in walked
    assert not any(name.startswith("bench/") for name in walked)


def test_a_named_key_is_seen_as_a_producer() -> None:
    """With ten of twelve budgets unproduced, the scanner's own sight needs a case."""
    assert _keys_named_in(['bus.publish("slider_to_preview", elapsed)']) == {"slider_to_preview"}
    assert _keys_named_in(["bus.publish(slider_to_preview, elapsed)"]) == set()


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


#: A budget is timed in CI if and only if some module in `tests/bench/` passes
#: its key to a `within_budget` call. Matching the call site rather than the key
#: alone is what keeps this from counting the meta-tests in this file, which
#: name every key by construction.
TIMED_CALL = re.compile(r'within_budget\(\s*"([a-z_]+)"')


@pytest.fixture(scope="module")
def asserted() -> set[str]:
    """Budget keys some benchmark in `tests/bench/` judges against a limit."""
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


def test_the_call_site_pattern_matches_a_call_and_not_a_mention() -> None:
    """`TIMED` is empty, so the pattern's own sight is the only thing holding it up.

    The positive case is assembled rather than written out because the
    `asserted` fixture scans this file too: a literal call site here would be a
    budget claiming a clock that no benchmark runs.
    """
    call = "    within_" + 'budget("slider_to_graph", median)'

    assert TIMED_CALL.findall(call) == ["slider_to_graph"]
    assert TIMED_CALL.findall("    within_budget(key)") == []
