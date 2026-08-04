"""Secret: how a named user operation becomes a graph.

Chunk 5. A tool never names an op or builds a graph — it states what it needs
(a ``Requirement``) and hands that to the resolver. See docs/DECISIONS.md,
2026-08-03.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from proto_sieve.src.sieve.kernel import Affine, Node
from proto_sieve.src.sieve.views import View, view_of


@dataclass(frozen=True)
class Requirement:
    """A sampling need: a coordinate map and an output shape. Not an op."""

    map: Affine
    out_shape: tuple[int, int]


class Tool:
    def requirement(self, params: object) -> Requirement:
        raise NotImplementedError

    def lower(self, params: object, source: Node) -> Node:
        """Requirement, resolved to an op, applied to ``source``."""
        from proto_sieve.src.sieve.resolver import resolve

        req = self.requirement(params)
        return Node(resolve(req), (source,))

    def view(self, result: np.ndarray) -> View:
        """A value describing ``result`` for display. Does not render it."""
        return view_of(result)
