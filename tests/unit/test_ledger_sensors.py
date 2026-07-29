








from __future__ import annotations

from dataclasses import fields

from sieve.core.shares import MEMORY_SHARES, SENSED, WITHOUT_SENSOR, WorkerSplit


def _every_row() -> set[str]:
    return {field.name for field in fields(WorkerSplit)} | {share.name for share in MEMORY_SHARES}


def test_every_row_is_sensed_or_declared_not_to_be() -> None:
    undeclared = _every_row() - SENSED - WITHOUT_SENSOR
    assert undeclared == set(), (
        "rows with no sensor must be declared in `concurrency.WITHOUT_SENSOR`; "
        f"undeclared: {sorted(undeclared)}"
    )


def test_the_two_lists_do_not_overlap() -> None:

    assert not SENSED & WITHOUT_SENSOR


def test_the_lists_name_only_real_rows() -> None:

    assert (SENSED | WITHOUT_SENSOR) - _every_row() == set()
