"""The first filter's kernel, against arithmetic rather than a reference image.

Downsample was chosen as the first filter because it can be checked this way:
the output shape is stated by the parameters, and with anti-aliasing off every
output pixel is a pixel that was in the input at a position you can name.
"""

from __future__ import annotations

import numpy as np
import pytest

from sieve.core.types import ChannelSpec, Frame
from sieve.filters.downsample import DownsampleParams, downsample_cpu


def gradient_frame(width: int, height: int) -> Frame:
    """A frame where pixel `(y, x)` holds a value unique to its position."""
    data = np.arange(height * width, dtype=np.uint16).reshape(height, width)
    return Frame(data=data, index=7, channels=ChannelSpec.GRAY)


def test_both_paths_agree_on_shape_when_the_factor_does_not_divide() -> None:
    # The one place the two kernel paths could disagree: a stride slice rounds
    # up where an INTER_AREA resize rounds down. If they diverge, `anti_alias`
    # silently changes the output *size* — a parameter documented as changing
    # only pixel values would be changing what every downstream shape check
    # sees, and `frame_bytes_ratio` would be right for one setting only.
    frame = gradient_frame(width=101, height=53)

    averaged = downsample_cpu(frame, DownsampleParams(factor=4, anti_alias=True))
    sampled = downsample_cpu(frame, DownsampleParams(factor=4, anti_alias=False))

    assert averaged.data.shape == sampled.data.shape == (13, 25)


def test_sampling_takes_the_block_origin_and_averaging_does_not() -> None:
    # What `anti_alias` actually decides, stated as pixels. Sampling is exact
    # and checkable in closed form; averaging is checked as "the block mean",
    # which is the claim the guidance markdown makes to the user.
    frame = gradient_frame(width=8, height=8)

    sampled = downsample_cpu(frame, DownsampleParams(factor=2, anti_alias=False))
    averaged = downsample_cpu(frame, DownsampleParams(factor=2, anti_alias=True))

    assert sampled.data[1, 3] == frame.data[2, 6]
    assert averaged.data[1, 3] == pytest.approx(frame.data[2:4, 6:8].mean(), abs=0.5)
    # Identity survives: a filter that renumbered frames would desynchronise
    # every downstream index without changing a pixel.
    assert (sampled.index, sampled.channels) == (frame.index, ChannelSpec.GRAY)


def test_a_factor_that_leaves_nothing_is_refused() -> None:
    # Reachable in practice, not a contrived bound: a replicate's ROI crop can
    # be a few dozen pixels, and the graph's downsample was set for the full
    # frame. Clamping to 1x1 would let a tuning session proceed against nothing.
    with pytest.raises(ValueError, match="leaves nothing of a 30x20 frame"):
        downsample_cpu(gradient_frame(width=30, height=20), DownsampleParams(factor=32))


def test_stored_bytes_prediction_matches_what_the_kernel_produced() -> None:
    # `frame_bytes_ratio` feeds VISION step 4's storage readout, and nothing
    # else checks it against a real frame. Loose because the declaration is
    # exact only when the factor divides both extents, which is the
    # approximation the docstring permits.
    frame = gradient_frame(width=640, height=480)
    params = DownsampleParams(factor=4)

    result = downsample_cpu(frame, params)

    assert result.data.nbytes / frame.data.nbytes == pytest.approx(
        params.frame_bytes_ratio(), rel=0.01
    )
