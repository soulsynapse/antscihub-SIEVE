"""Live-repo tests: the automatic ledger's mismatch check and the sentinel.

Unlike tests/test_debt.py, these run against the repository itself.
"""

from pathlib import Path

import pytest

from sieve.debt import (
    FILE_QUALNAME,
    LEDGER_NAME,
    MODULE_QUALNAME,
    SENTINEL_ROOT,
    enumerate_markers,
    entry_diff,
    parse,
    parse_stamp,
    serialize,
    stamp_landings,
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


def test_sentinel_is_excluded_from_the_default_enumeration():
    leaked = [e for e in enumerate_markers(REPO_ROOT) if e.path.startswith(SENTINEL_ROOT)]
    assert not leaked, (
        "the sentinel leaked into the default enumeration; it is a liveness "
        "proof, not debt -- do not regenerate it into the ledger"
    )


def test_sentinel_markers_are_found_on_both_surfaces():
    found = enumerate_markers(REPO_ROOT, roots=(SENTINEL_ROOT,), excluded=())
    assert [(e.path, e.qualname) for e in found] == [
        (f"{SENTINEL_ROOT}/marker.md", FILE_QUALNAME),
        (f"{SENTINEL_ROOT}/marker.py", MODULE_QUALNAME),
    ], "a sentinel marker was not found: that surface's scanner cannot be trusted"


def test_stamps_do_not_postdate_their_own_landing():
    """The history-dependent half of the stamp audit (PAR-0002): a stamp
    states when the debt was written down, so it must precede the commit
    that first landed it in the ledger. Backdated stamps are fine;
    fabricated ones convict themselves. First-appearance only, so a
    restated marker keeping its old stamp never trips this."""
    if not (REPO_ROOT / ".git").exists():
        pytest.skip("no git checkout: the stamp-landing audit needs history")
    from datetime import timedelta

    landings = stamp_landings(REPO_ROOT)
    for entry in enumerate_markers(REPO_ROOT):
        landed = landings.get(entry.stamp)
        if landed is None:
            continue  # not yet committed; the static future-check covers it
        stated = parse_stamp(entry.stamp)
        assert stated <= landed + timedelta(minutes=5), (
            f"{entry.path}::{entry.qualname}: stamp {entry.stamp} postdates "
            f"its own first ledger appearance ({landed.isoformat()})"
        )
