"""Secret: how a named user operation becomes a graph (chunk 5, shared with
``tools/base.py``). Crop states the window it needs; it never picks an op.
"""

from __future__ import annotations

from dataclasses import dataclass

from proto_sieve.src.sieve.kernel import Affine
from proto_sieve.src.sieve.tools.base import Requirement, Tool


@dataclass(frozen=True)
class CropParams:
    y0: int
    y1: int
    x0: int
    x1: int


class Crop(Tool):
    def requirement(self, params: CropParams) -> Requirement:
        m = Affine((1.0, 0.0, float(params.x0), 0.0, 1.0, float(params.y0)))
        return Requirement(map=m, out_shape=(params.y1 - params.y0, params.x1 - params.x0))
