"""Sentinel: liveness proof for the marker enumerator; not debt.

Excluded from the default enumeration; tests/test_automatic_ledger.py
enumerates this directory explicitly and must find exactly the two
sentinel markers (this file and marker.md).
"""

from sieve.debt import Owed

raise Owed("20260802T005044Z: sentinel: the enumerator is alive")
