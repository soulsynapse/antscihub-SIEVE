"""background: one composite of rows spaced over the clip, by mean or median, the same at every row and rebuilt on a new key."""
from types import SimpleNamespace

import numpy as np

from tools import background


def clip(count, key="k"):
    d = np.full((count, 4, 4), 10, np.uint8)
    d[:3, 1, 1] = 250                                      # a thing that sits in the first three rows only
    reads = []

    class Frames(SimpleNamespace):
        def __call__(self, r, input="in"):
            reads.append(r)
            return d[r]

    return Frames(key=key, count=count, fps=1.0), reads


def test_sample_rows_span_the_clip_and_never_exceed_it():
    assert background.sample_rows(100, 5).tolist() == [0, 25, 50, 74, 99]
    assert background.sample_rows(3, 50).tolist() == [0, 1, 2] and background.sample_rows(1, 0).tolist() == [0]


def test_median_drops_the_transient_mean_smears_it_and_one_build_serves_every_row():
    frames, reads = clip(20)
    out = background.run(frames, 7, {"stat": "median", "samples": 5})
    assert out.dtype == np.uint8 and out[1, 1] == 10 and out[0, 0] == 10 and reads == [0, 5, 10, 14, 19]
    assert background.run(frames, 3, {"stat": "median", "samples": 5}) is out and len(reads) == 5   # same key: no reads
    out = background.run(frames, 0, {"stat": "mean", "samples": 5})
    assert out.dtype == np.uint8 and out[1, 1] == 58 and len(reads) == 10                      # (250 + 4 * 10) / 5
    frames.key = "other"
    background.run(frames, 0, {"stat": "mean", "samples": 5})
    assert len(reads) == 15                                                                    # upstream changed: rebuilt
