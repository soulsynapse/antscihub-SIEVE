from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


Float32Array = NDArray[np.float32]


@dataclass(frozen=True, slots=True)
class ChannelFrame:
    """One immutable, computed channel field suitable for live presentation.

    Final scientific results remain the authoritative retained artifact. This
    small callback value lets a caller present accepted frames while the same
    computation is still filling that final result.
    """

    absolute_frame: int
    values: Float32Array
    valid: bool = True

    def __post_init__(self) -> None:
        values = np.asarray(self.values, dtype=np.float32)
        if values.ndim != 2:
            raise ValueError("ChannelFrame values must be two-dimensional")
        if not np.all(np.isfinite(values)):
            raise ValueError("ChannelFrame values must be finite")
        owned = np.ascontiguousarray(values)
        owned.setflags(write=False)
        object.__setattr__(self, "values", owned)


FrameCompletedCallback = Callable[[ChannelFrame], None]
