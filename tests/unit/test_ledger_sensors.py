"""Rule 4's other half, for the concurrency ledger's own tables.

`test_budget_producers.py` holds the latency table to "a producer or a
declared gap, never silently neither"; this holds the worker-split and
memory-share tables to the same standard. The rows are derived from the
tables, not restated here, so a new pool or share fails this test until the
commit that creates it also says whether anything can measure it.
"""

from __future__ import annotations

from dataclasses import fields

from sieve.mutual.shares import MEMORY_SHARES, SENSED, WITHOUT_SENSOR, WorkerSplit


def _every_row() -> set[str]:
    return {field.name for field in fields(WorkerSplit)} | {share.name for share in MEMORY_SHARES}


def test_every_row_is_sensed_or_declared_not_to_be() -> None:
    undeclared = _every_row() - SENSED - WITHOUT_SENSOR
    assert undeclared == set(), (
        "rows with no sensor must be declared in `concurrency.WITHOUT_SENSOR`; "
        f"undeclared: {sorted(undeclared)}"
    )


def test_the_two_lists_do_not_overlap() -> None:
    """A row cannot be both measured and declared unmeasurable."""
    assert not SENSED & WITHOUT_SENSOR


def test_the_lists_name_only_real_rows() -> None:
    """A stale name would hold a gap open for a row that no longer exists."""
    assert (SENSED | WITHOUT_SENSOR) - _every_row() == set()
