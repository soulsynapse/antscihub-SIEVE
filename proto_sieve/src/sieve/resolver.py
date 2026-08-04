"""Secret: how a requirement becomes an op.

Chunk 5. The resolver is the only thing in this spike that knows ``Slice``
and ``Resample`` can mean the same pixels — a tool never makes that choice,
it only states what it needs.
"""

from __future__ import annotations

from proto_sieve.src.sieve.kernel import Affine, Resample, Slice
from proto_sieve.src.sieve.tools.base import Requirement


def _is_unit_translation(m: Affine) -> bool:
    a, b, c, d, e, f = m.m
    return (
        a == 1.0
        and b == 0.0
        and d == 0.0
        and e == 1.0
        and c == int(c)
        and f == int(f)
    )


def resolve(req: Requirement) -> object:
    """A requirement to a concrete op. ``Slice`` whenever it is a free swap."""
    if _is_unit_translation(req.map):
        x0, y0 = int(req.map.m[2]), int(req.map.m[5])
        h, w = req.out_shape
        return Slice(y0, y0 + h, x0, x0 + w)
    return Resample(req.map, req.out_shape)
