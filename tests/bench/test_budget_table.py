"""The budget table in code agrees with the budget table in the architecture.

[INTENT] `sieve.bench.budgets` is a transcription, and a transcription that
nothing checks is a copy that drifts. This is the mechanism behind the digest
rule that sources win on disagreement: edit section 1 and this fails, naming
the row that moved.

Fast, Qt-free, and not marked `slow`, so it runs in `nox -s checks` rather than
only when someone remembers to run the benchmark session. The drift it catches
is a documentation edit, and documentation edits do not wait for a benchmark
machine. `--benchmark-only` deselects it from `nox -s benchmark`, which is
correct: it measures nothing.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from sieve.bench.budgets import BUDGETS, REGRESSION_MARGIN, Budget, Regime

ARCHITECTURE = Path(__file__).resolve().parents[2] / "docs" / "04-architecture" / "ARCHITECTURE.md"

# "| File open → first frame visible | < 500 ms | pre-pipeline |"
ROW = re.compile(
    r"^\|\s*(?P<interaction>[^|]+?)\s*\|\s*<\s*(?P<value>[\d.]+)\s*(?P<unit>ms|s)\s*\|"
    r"\s*(?P<regime>pre-pipeline|in-pipeline)\s*\|\s*$"
)
UNIT_MS = {"ms": 1.0, "s": 1000.0}


# Typographic differences between the prose and the module, which are not drift.
# The document is markdown and uses the fancy forms; the module is source, read
# in terminals that do not all render them. Failing on these would train a
# reader to dismiss this test, and the numbers are what it exists to protect.
#
# RUF001 flags ambiguous characters, which is exactly what these are and
# exactly why the mapping exists. This is the one place in the repo where the
# ambiguity is the subject rather than a defect, so it is suppressed here and
# nowhere else.
TYPOGRAPHY = {
    "→": "->",  # rightwards arrow
    "–": "-",  # noqa: RUF001 -- en dash, the one Ruff reads as a hyphen
    "—": "-",  # em dash
}


def _normalize(interaction: str) -> str:
    """Compare on content, not on typography."""
    for fancy, plain in TYPOGRAPHY.items():
        interaction = interaction.replace(fancy, plain)
    return re.sub(r"\s+", " ", interaction).strip().casefold()


def _parse_architecture_table() -> list[tuple[str, float, Regime]]:
    if not ARCHITECTURE.is_file():
        pytest.fail(f"ARCHITECTURE.md is not at {ARCHITECTURE}; the budget table has no source.")
    rows: list[tuple[str, float, Regime]] = []
    for line in ARCHITECTURE.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if match is None:
            continue
        rows.append(
            (
                _normalize(match["interaction"]),
                float(match["value"]) * UNIT_MS[match["unit"]],
                Regime(match["regime"]),
            )
        )
    return rows


def test_the_table_is_findable() -> None:
    """A parser that silently matches nothing would make every other test here vacuous."""
    rows = _parse_architecture_table()
    assert len(rows) == len(BUDGETS), (
        f"Parsed {len(rows)} budget rows from ARCHITECTURE.md section 1 but "
        f"sieve.bench.budgets declares {len(BUDGETS)}. Either a row was added or "
        "removed in the document, or the table's formatting changed under the parser."
    )


@pytest.mark.parametrize("entry", list(BUDGETS.values()), ids=lambda entry: entry.key)
def test_each_budget_matches_its_source_row(entry: Budget) -> None:
    rows = {interaction: (ms, regime) for interaction, ms, regime in _parse_architecture_table()}
    key = _normalize(entry.interaction)
    assert key in rows, (
        f"Budget {entry.key!r} cites the interaction {entry.interaction!r}, which no "
        f"longer appears in ARCHITECTURE.md section 1. Known rows: {sorted(rows)}"
    )
    milliseconds, regime = rows[key]
    assert entry.milliseconds == milliseconds
    assert entry.regime is regime


def test_regression_margin_matches_the_stated_policy() -> None:
    text = ARCHITECTURE.read_text(encoding="utf-8")
    percent = round(REGRESSION_MARGIN * 100)
    assert f"{percent}%" in text, (
        f"sieve.bench.budgets sets REGRESSION_MARGIN to {percent}%, which no longer "
        "appears in ARCHITECTURE.md. Section 1 states the justification threshold."
    )
