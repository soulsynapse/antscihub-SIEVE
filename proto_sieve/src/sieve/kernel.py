"""Secret: how an op is represented.

Chunk 1 (and chunk 2, identity). Nothing outside this module may depend on the canonical form, the digest
algorithm, or the field layout of an op. What it may depend on is that
``recipe_hash`` is a pure function of the graph's value and is stable across
processes, machines, and runs.

The scheme version is in the digest from the first commit. Without it, changing
what the hash covers orphans every stored result; with it, that change costs a
migration you can actually write.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass
from typing import Any

HASH_SCHEME_VERSION = 1


# --- op values ---------------------------------------------------------------
# An op is a value: frozen, structurally compared, carrying no behaviour and no
# module path. Where its implementation lives is not in the hash, which is what
# makes moving one cost a file move rather than a store migration.


@dataclass(frozen=True)
class Affine:
    """Row-major 2x3 coordinate map: (a, b, c, d, e, f)."""

    m: tuple[float, float, float, float, float, float]


@dataclass(frozen=True)
class Source:
    """A named input to the graph. The leaf."""

    name: str


@dataclass(frozen=True)
class Resample:
    """Sample the input through an affine coordinate map into ``out_shape``."""

    map: Affine
    out_shape: tuple[int, int]


@dataclass(frozen=True)
class Slice:
    """Take a rectangular window by index. Rows ``[y0:y1]``, cols ``[x0:x1]``.

    Bit-identical to ``Resample`` whenever the map is a unit-scale integer
    translation — which is what makes it a free swap, and what makes "does the
    resolved op enter the hash" a real question rather than a hypothetical.
    """

    y0: int
    y1: int
    x0: int
    x1: int


@dataclass(frozen=True)
class Blur:
    """Isotropic gaussian blur.

    Not evaluable in this spike. It exists so identity has two ops with the
    same field shape to tell apart; giving it an implementation would be
    scope the decomposition does not need proving.
    """

    sigma: float


@dataclass(frozen=True)
class Sharpen:
    """Unsharp mask. Same param shape as ``Blur`` on purpose: identity must
    separate them by op, never by field layout."""

    sigma: float


@dataclass(frozen=True)
class Node:
    """An op applied to inputs. A graph is a Node."""

    op: Any
    inputs: tuple["Node", ...] = ()


# --- the recipe hash ---------------------------------------------------------


def _canon(value: Any) -> Any:
    """Canonical JSON-able form. Deterministic across processes by construction.

    The type name is carried as ``$`` so two ops with identical field names and
    values never collide. Nothing here touches ``hash()``, ``id()``, or dict
    iteration order.
    """
    if is_dataclass(value) and not isinstance(value, type):
        out = {"$": type(value).__name__}
        for f in fields(value):
            out[f.name] = _canon(getattr(value, f.name))
        return out
    if isinstance(value, (tuple, list)):
        return [_canon(v) for v in value]
    if isinstance(value, dict):
        return {"$map": [[_canon(k), _canon(v)] for k, v in sorted(value.items())]}
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"not canonicalizable: {type(value).__name__}")


def recipe_hash(node: Node) -> str:
    """The address of a graph's result. Pure function of the graph's value."""
    payload = {"scheme": HASH_SCHEME_VERSION, "graph": _canon(node)}
    blob = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
