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

#: Discovered filters this probe cannot verify, and so does not claim to.
#: Shrink-only, the `WITHOUT_PRODUCER` construction. `detect` is here because
#: its published value is its span's *last* frame, which by construction is
#: never settled: the kernel returns NaN at every span length, so two origins
#: agree on nothing. It leaves this list when the kernel publishes a sample it
#: can stand behind (`docs/todo/the-detect-kernel-publishes-an-unsettled-sample.md`).
WITHOUT_SETTLING_PRODUCER: frozenset[tuple[str, str]] = frozenset({("detect", "1.0.0")})

DISCOVERED = discover()


def _shaped_for_the_probe(spec: FilterSpec) -> bool:
    """Whether the generic single-array probe can call this filter at all."""
    return (
        len(spec.input_ports) == 1
        and all(isinstance(stream, ArraySpec) for stream in spec.input_ports.values())
        and isinstance(spec.emits, ArraySpec)
        and Backend.CPU in KERNELS.backends_for(spec)
    )


def _yields_a_comparable_sample(spec: FilterSpec) -> bool:
    """Whether the probe gets a value back that two origins could disagree on.

    The second half of probeability, and the half a structural test cannot
    see. A filter whose output is entirely NaN passes `np.allclose(...,
    equal_nan=True)` against anything — including itself — so counting it as
    verified is rule 6 at the level of the gate: unexamined rendering as quiet.
    """
    params = spec.params_model()
    target = node_warmup_frames((spec, params)).frames + 1
    produced = _runner(spec)(spec, params, 0, target)
    return not bool(np.isnan(np.asarray(produced.data, dtype=np.float64)).all())


def _unverifiable(spec: FilterSpec) -> bool:
    return not _shaped_for_the_probe(spec) or not _yields_a_comparable_sample(spec)


PROBED = tuple(spec for spec in DISCOVERED if spec.key not in WITHOUT_SETTLING_PRODUCER)


def test_the_unverified_set_names_exactly_the_filters_the_probe_cannot_verify() -> None:
    assert set(WITHOUT_SETTLING_PRODUCER) == {
        spec.key for spec in DISCOVERED if _unverifiable(spec)
    }


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
    """`target`'s output from a span beginning at `start`.

    The span is *not* re-clamped to the declared window. Clamping is what made
    this vacuous: with `first = max(start, target - window + 1)` and a target
    of `start + warmup + extra`, both origins resolved to the same first frame,
    so the two-origin comparison was a run against itself. Handing the
    later-origin run the minimum and the frame-zero run everything before it is
    the whole claim — history older than the declared window must not matter.
    """
    run = cast(WindowedKernel[ParamsBase], KERNELS.select(spec, (Backend.CPU,)).start())
    span = FrameSpan(tuple(_frame(index) for index in range(start, target + 1)))
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
    # Before the agreement: something to agree *on*. `equal_nan=True` is right
    # for a filter whose output is partly undefined and wrong as a whole-array
    # verdict — two all-NaN arrays are "close" to each other and to nothing.
    assert not np.isnan(np.asarray(from_zero.data, dtype=np.float64)).all()
    epsilon = 0.0 if spec.settling_epsilon is None else spec.settling_epsilon
    assert np.allclose(from_zero.data, from_later.data, rtol=0.0, atol=epsilon, equal_nan=True)
