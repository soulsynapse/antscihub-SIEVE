"""Secret: which frame corresponds to which step, right now.

Truncate the pipeline to its first ``index + 1`` steps, lower, render.
Nothing here caches beyond what ``executor.render`` already does — two
truncations sharing a prefix hash to the same nodes, so stepping through a
pipeline (or undoing to an earlier one) reuses the executor's cache for free.
An index of ``-1`` means no steps yet: the bound source, unmodified.
"""

from __future__ import annotations

import numpy as np

from proto_sieve.src.sieve.executor import render
from proto_sieve.src.sieve.pipeline import Pipeline, lower


def frame_for(pipeline: Pipeline, index: int, bound: dict[str, np.ndarray]) -> np.ndarray:
    truncated = Pipeline(pipeline.source, pipeline.steps[: index + 1])
    return render(lower(truncated), bound)
