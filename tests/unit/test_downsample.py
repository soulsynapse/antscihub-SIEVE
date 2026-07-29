






from __future__ import annotations

import numpy as np
import pytest

from sieve.core.types import ChannelSpec, Frame
from sieve.filters.downsample import DownsampleParams, downsample_cpu


def gradient_frame(width: int, height: int) -> Frame:

    data = np.arange(height * width, dtype=np.uint16).reshape(height, width)
    return Frame(data=data, index=7, channels=ChannelSpec.GRAY)


def test_both_paths_agree_on_shape_when_the_factor_does_not_divide() -> None:





    frame = gradient_frame(width=101, height=53)

    averaged = downsample_cpu(frame, DownsampleParams(factor=4, anti_alias=True))
    sampled = downsample_cpu(frame, DownsampleParams(factor=4, anti_alias=False))

    assert averaged.data.shape == sampled.data.shape == (13, 25)


def test_sampling_takes_the_block_origin_and_averaging_does_not() -> None:



    frame = gradient_frame(width=8, height=8)

    sampled = downsample_cpu(frame, DownsampleParams(factor=2, anti_alias=False))
    averaged = downsample_cpu(frame, DownsampleParams(factor=2, anti_alias=True))

    assert sampled.data[1, 3] == frame.data[2, 6]
    assert averaged.data[1, 3] == pytest.approx(frame.data[2:4, 6:8].mean(), abs=0.5)


    assert (sampled.index, sampled.channels) == (frame.index, ChannelSpec.GRAY)


def test_a_factor_that_leaves_nothing_is_refused() -> None:



    with pytest.raises(ValueError, match="leaves nothing of a 30x20 frame"):
        downsample_cpu(gradient_frame(width=30, height=20), DownsampleParams(factor=32))


def test_stored_bytes_prediction_matches_what_the_kernel_produced() -> None:




    frame = gradient_frame(width=640, height=480)
    params = DownsampleParams(factor=4)

    result = downsample_cpu(frame, params)

    assert result.data.nbytes / frame.data.nbytes == pytest.approx(
        params.frame_bytes_ratio(), rel=0.01
    )
