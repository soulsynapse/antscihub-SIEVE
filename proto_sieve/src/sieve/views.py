"""Secret: how a result is described for display.

Chunk 7. A view is a value: a pure function of the rendered array, structurally
compared, holding no reference to it. It does not render anything — nothing
outside this module may depend on a view carrying pixel data, a tool identity,
or the params that produced the result it describes.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class View:
    shape: tuple[int, int]
    dtype: str


def view_of(result: np.ndarray) -> View:
    rows, cols = result.shape[0], result.shape[1]
    return View(shape=(rows, cols), dtype=str(result.dtype))
