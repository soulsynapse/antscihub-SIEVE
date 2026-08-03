"""The kernel: ops as values, and the proved forms (PAR-0005).

An op is a serializable value -- a closed constructor with typed
fields -- never a callable; Opaque(fn) is the sole exception and the
zero-reading conformance path. The form an op is written in is an
authorization: which substitutions the executor may make silently,
proved under the answer defined at the logical level. The vocabulary
is what has been proved, and no more:

    affine coordinate map   exact map over (t, y, x)
    the sequential bit      structural; a sweep barrier
    Opaque                  no structure exposed; never fused

A further form is admitted when a substitution it would license is
both wanted and provable (PAR-0005 "The vocabulary"); DEFERRED.md
holds the intended factoring for stateful and windowed ops.
"""

from sieve.debt import Owed

raise Owed(
    "20260802T023505Z: ops as values and the proved forms (affine coordinate map, the"
    " sequential bit, Opaque) as one design unit; PAR-0005 'Decision',"
    " ARCHITECTURE.md 'The components'"
)
