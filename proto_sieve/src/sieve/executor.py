"""Secret: how a graph is evaluated — traversal order, intermediate buffers,
and (from chunk 4) whether a result was computed or retrieved.

Chunk 3 and chunk 4. The executor decides nothing. It does not choose ops, it does not substitute,
it does not measure. Every decision of that kind belongs to the resolver, which
runs before evaluation and hands this module a graph of concrete ops. That
split is the correction to treating substitution as an executor concern.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict

import numpy as np

from proto_sieve.src.sieve.kernel import Node, Resample, Slice, Source, recipe_hash

CACHE_ENTRIES = 64

_cache: "OrderedDict[tuple[str, str], np.ndarray]" = OrderedDict()
_hits = 0
_misses = 0


def cache_stats() -> dict[str, int]:
    """Instrumentation. Says how an answer arrived, never what it is."""
    return {"hits": _hits, "misses": _misses, "entries": len(_cache)}


def clear_cache() -> None:
    global _hits, _misses
    _cache.clear()
    _hits = _misses = 0


def _bound_digest(bound: dict[str, np.ndarray]) -> str:
    """Content digest of the bound inputs.

    The recipe hash addresses the *graph*; it says nothing about what was bound
    to its sources. Keying on the recipe alone would serve frame 0's answer for
    every frame after it. Coarse on purpose — any input changing invalidates
    the lot — and the cost of hashing every frame on every call is a real
    finding, not an implementation detail (see FINDINGS.md).
    """
    h = hashlib.sha256()
    for name in sorted(bound):
        arr = np.ascontiguousarray(bound[name])
        h.update(name.encode("utf-8"))
        h.update(str(arr.dtype).encode("utf-8"))
        h.update(repr(arr.shape).encode("utf-8"))
        h.update(arr.tobytes())
    return h.hexdigest()


def _resample(src: np.ndarray, op: Resample) -> np.ndarray:
    rows, cols = op.out_shape
    a, b, c, d, e, f = op.map.m
    oy, ox = np.mgrid[0:rows, 0:cols]
    ix = np.rint(a * ox + b * oy + c).astype(np.intp)
    iy = np.rint(d * ox + e * oy + f).astype(np.intp)
    np.clip(ix, 0, src.shape[1] - 1, out=ix)
    np.clip(iy, 0, src.shape[0] - 1, out=iy)
    return src[iy, ix]


def _apply(op: object, inputs: list[np.ndarray], bound: dict[str, np.ndarray]):
    if isinstance(op, Source):
        return bound[op.name]
    if isinstance(op, Slice):
        return inputs[0][op.y0 : op.y1, op.x0 : op.x1]
    if isinstance(op, Resample):
        return _resample(inputs[0], op)
    raise NotImplementedError(f"no implementation for {type(op).__name__}")


def render(node: Node, bound: dict[str, np.ndarray]) -> np.ndarray:
    """Evaluate ``node`` against the named input frames.

    The signature is unchanged from chunk 3. Callers do not create caches, do
    not pass them, and cannot tell whether one was used.
    """
    return _render(node, bound, _bound_digest(bound))


def _render(node: Node, bound: dict[str, np.ndarray], stamp: str) -> np.ndarray:
    global _hits, _misses
    key = (recipe_hash(node), stamp)
    if key in _cache:
        _hits += 1
        _cache.move_to_end(key)
        return _cache[key]

    _misses += 1
    inputs = [_render(child, bound, stamp) for child in node.inputs]
    out = _apply(node.op, inputs, bound)

    _cache[key] = out
    _cache.move_to_end(key)
    while len(_cache) > CACHE_ENTRIES:
        _cache.popitem(last=False)
    return out
