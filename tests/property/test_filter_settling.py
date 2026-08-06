"""R3's gate: warmup claims make two origins agree.

The property is over the discovered shelf, not over hand-picked filters. A
filter that cannot be exercised by this generic single-array probe must enter
`WITHOUT_SETTLING_PRODUCER`, which is the shrink-only work list.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from sieve.backend.dispatch import KERNELS, Backend, Kernel, WindowedKernel
from sieve.core.filter_base import ArraySpec, FilterSpec, Mode, ParamsBase, node_warmup_frames
from sieve.core.types import ChannelSpec, Frame, FrameSpan
from sieve.filters import discover

WIDTH, HEIGHT = 48, 36

WITHOUT_SETTLING_PRODUCER: frozenset[tuple[str, str]] = frozenset()

DISCOVERED = discover()


def _probeable(spec: FilterSpec) -> bool:
    return (
        len(spec.input_ports) == 1
        and all(isinstance(stream, ArraySpec) for stream in spec.input_ports.values())
        and isinstance(spec.emits, ArraySpec)
        and Backend.CPU in KERNELS.backends_for(spec)
    )


PROBED = tuple(spec for spec in DISCOVERED if spec.key not in WITHOUT_SETTLING_PRODUCER)


def test_the_unverified_set_names_exactly_the_unprobeable_discovered_filters() -> None:
    unprobeable = {spec.key for spec in DISCOVERED if not _probeable(spec)}
    assert set(WITHOUT_SETTLING_PRODUCER) == unprobeable


def _frame(index: int) -> Frame:
    rows = np.arange(HEIGHT, dtype=np.float32)[:, None]
    cols = np.arange(WIDTH, dtype=np.float32)[None, :]
    phase = np.float32((index % 23) / 23.0)
    data = (0.2 + 0.5 * phase + rows * np.float32(0.001) + cols * np.float32(0.002)).astype(
        np.float32
    )
    return Frame(data=data, index=index, channels=ChannelSpec.GRAY)


def _streaming_output(spec: FilterSpec, params: ParamsBase, start: int, target: int) -> Frame:
    run = cast(Kernel[ParamsBase], KERNELS.select(spec, (Backend.CPU,)).start())
    produced = _frame(start)
    for index in range(start, target + 1):
        produced = run(_frame(index), params)
    return produced


def _windowed_output(spec: FilterSpec, params: ParamsBase, start: int, target: int) -> Frame:
    run = cast(WindowedKernel[ParamsBase], KERNELS.select(spec, (Backend.CPU,)).start())
    window = node_warmup_frames((spec, params)).frames + 1
    first = max(start, target - window + 1)
    span = FrameSpan(tuple(_frame(index) for index in range(first, target + 1)))
    return run(span, params)


def _runner(spec: FilterSpec) -> Callable[[FilterSpec, ParamsBase, int, int], Frame]:
    if spec.mode is Mode.WINDOWED:
        return _windowed_output
    return _streaming_output


@pytest.mark.parametrize("spec", PROBED, ids=lambda spec: f"{spec.filter_id}-{spec.version}")
@settings(max_examples=4, deadline=None)
@given(
    later_start=st.integers(min_value=1, max_value=5),
    extra_frames=st.integers(min_value=0, max_value=3),
)
def test_discovered_filters_agree_after_their_declared_warmup(
    spec: FilterSpec, later_start: int, extra_frames: int
) -> None:
    params = spec.params_model()
    warmup = node_warmup_frames((spec, params))
    target = later_start + warmup.frames + extra_frames

    run = _runner(spec)
    from_zero = run(spec, params, 0, target)
    from_later = run(spec, params, later_start, target)

    assert from_zero.index == from_later.index == target
    assert from_zero.data.shape == from_later.data.shape
    epsilon = 0.0 if spec.settling_epsilon is None else spec.settling_epsilon
    assert np.allclose(from_zero.data, from_later.data, rtol=0.0, atol=epsilon, equal_nan=True)
