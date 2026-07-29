

from __future__ import annotations

import cv2
import numpy as np
import pytest

from sieve.core.types import ChannelSpec, Frame
from sieve.filters.normalize import NormalizeMode, NormalizeParams, normalize_cpu
from sieve.filters.rescale import RescaleParams, rescale_cpu


def test_rescale_rounds_each_extent_and_preserves_dtype() -> None:




    data = np.random.default_rng(0).integers(0, 255, (53, 101), np.uint8)
    frame = Frame(data=data, index=3, channels=ChannelSpec.GRAY)

    out = rescale_cpu(frame, RescaleParams(scale=0.25))

    assert out.data.shape == (13, 25)
    assert out.data.dtype == np.uint8
    assert (out.index, out.channels) == (3, ChannelSpec.GRAY)


def test_rescale_at_one_is_the_identity_object() -> None:


    frame = Frame(data=np.zeros((10, 10), np.uint8), index=0, channels=ChannelSpec.GRAY)
    assert rescale_cpu(frame, RescaleParams(scale=1.0)) is frame


def test_zscore_hits_target_mean_and_sd() -> None:

    rng = np.random.default_rng(1)
    data = rng.integers(0, 255, (64, 64), np.uint8)
    frame = Frame(data=data, index=0, channels=ChannelSpec.GRAY)

    out = normalize_cpu(frame, NormalizeParams(mode=NormalizeMode.ZSCORE))

    assert out.data.dtype == np.float32
    assert float(out.data.mean()) == pytest.approx(128.0, abs=0.01)
    assert float(out.data.std()) == pytest.approx(32.0, abs=0.01)


def test_zscore_of_a_constant_frame_centers_without_dividing() -> None:


    frame = Frame(data=np.full((32, 32), 7.0, np.float32), index=0, channels=ChannelSpec.GRAY)

    out = normalize_cpu(frame, NormalizeParams(mode=NormalizeMode.ZSCORE))

    assert np.isfinite(out.data).all()
    np.testing.assert_allclose(out.data, 0.0, atol=1e-5)


def test_zscore_on_bgr_normalizes_the_downstream_gray_series() -> None:





    rng = np.random.default_rng(2)


    data = np.stack(
        [
            rng.normal(40, 10, (48, 48)),
            rng.normal(120, 30, (48, 48)),
            rng.normal(200, 5, (48, 48)),
        ],
        axis=-1,
    ).astype(np.float32)
    frame = Frame(data=data, index=0, channels=ChannelSpec.BGR)

    out = normalize_cpu(frame, NormalizeParams(mode=NormalizeMode.ZSCORE))

    gray = cv2.cvtColor(out.data, cv2.COLOR_BGR2GRAY)
    assert float(gray.mean()) == pytest.approx(128.0, abs=0.05)
    assert float(gray.std()) == pytest.approx(32.0, abs=0.05)
