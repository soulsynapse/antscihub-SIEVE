"""The conformance suite: a placeholder like any other component.

Owed: every tool round-trips its params, defaults validate, ports
resolve, and migration succeeds from every historical version
(DESIGN-SESSION.md Exchange 1); plus the two closed property tests --
any Resample chain bit-identical fused and unfused, Window frame N
identical cold and during a sweep (Exchange 5, "Testing becomes closed
too"). Collection of this module skips whole, carrying this reason,
until the suite is real.
"""

from sieve.debt import Owed

raise Owed(
    "conformance suite: params round-trip, migration corpus, fused-vs-"
    "unfused and Window cold-vs-sweep property tests; DESIGN-SESSION.md"
    " Exchanges 1 and 5"
)
