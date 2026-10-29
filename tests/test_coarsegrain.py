"""coarsegrain: one value per cell by method, the edge cells partial; a flow field per component."""
import numpy as np
import pytest

from tools import coarsegrain


def test_each_method_over_the_cells_with_a_partial_edge():
    a = np.zeros((5, 6), np.uint8)
    a[:2, :2] = 200                                        # the first 2x2 cell is full
    a[4, 5] = 100                                          # the corner cell is 1x2 and half set
    frames = lambda r: a  # noqa: E731
    want = {"mean": (200.0, 50.0), "sum": (800.0, 100.0), "max": (200.0, 100.0), "fraction": (1.0, 0.5)}
    for m, (first, corner) in want.items():
        out = coarsegrain.run(frames, 0, {"block": 2, "method": m})
        assert out.shape == (3, 3) and out.dtype == np.float32, m
        assert (out[0, 0], out[2, 2], out[1, 1]) == (first, corner, 0.0), m
    with pytest.raises(ValueError):
        coarsegrain.run(frames, 0, {"block": 2, "method": "median"})


def test_a_flow_field_is_cellled_per_component_and_only_by_a_vector_method():
    f = np.zeros((4, 4, 2), np.float32)
    f[:2, :2] = (1.0, -3.0)
    f[0, 0] = (3.0, -1.0)
    frames = lambda r: f  # noqa: E731
    out = coarsegrain.run(frames, 0, {"block": 2, "method": "mean"})
    assert out.shape == (2, 2, 2) and out[0, 0].tolist() == [1.5, -2.5] and not out[1, 1].any()
    with pytest.raises(ValueError):
        coarsegrain.run(frames, 0, {"block": 2, "method": "max"})
