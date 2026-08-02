"""Live-repo tests: the automatic ledger's mismatch check and the sentinel.

Unlike tests/test_debt.py, these run against the repository itself.
"""

from pathlib import Path

import pytest

from sieve.debt import (
    LEDGER_NAME,
    MODULE_QUALNAME,
    SENTINEL_ROOT,
    enumerate_markers,
    entry_diff,
    parse,
    serialize,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_automatic_ledger_matches_a_fresh_enumeration():
    entries = enumerate_markers(REPO_ROOT)
    ledger_path = REPO_ROOT / LEDGER_NAME
    if not ledger_path.is_file():
        pytest.fail(f"{LEDGER_NAME} is missing; generate it: python -m sieve.debt write")
    checked_in = ledger_path.read_bytes()
    fresh = serialize(entries)
    if fresh != checked_in:
        diff = entry_diff(parse(checked_in), entries) or (
            "no entry-level difference: the divergence is in the header or "
            "formatting (version pin changed without a regen? hand edit?)"
        )
        pytest.fail(
            f"{LEDGER_NAME} does not match a fresh enumeration.\n"
            + diff
            + "\nExpected change: run `python -m sieve.debt write`."
            " Unexpected change: investigate before regenerating."
        )


def test_sentinel_marker_is_found():
    found = enumerate_markers(REPO_ROOT, roots=(SENTINEL_ROOT,), excluded=())
    assert [(e.path, e.qualname) for e in found] == [
        (f"{SENTINEL_ROOT}/marker.py", MODULE_QUALNAME)
    ], "the sentinel marker was not found: the enumerator cannot be trusted"
