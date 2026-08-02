"""Sentinel: liveness proof for the marker enumerator; not debt.

Excluded from the default enumeration roots; tests/test_automatic_ledger.py
enumerates this directory explicitly and must find exactly this marker.
"""

from sieve.debt import Owed

raise Owed("sentinel: the enumerator is alive")
