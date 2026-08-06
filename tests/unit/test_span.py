"""The span filter: what it declares, what it refuses, and what it does not cut.

Each test stands for a way the span stops being a filter. The identity span is
what keeps `range | None` out of the plan. The declared range is the *only*
statement of which frames are in the answer, so a params model that failed to
carry it would leave the plan folding nothing while the node still looked live.
And the kernel passing the lead-in through is the half that reads like a bug and
is the design: cut those frames here and every stateful filter downstream of the
node runs the whole span unsettled.
"""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from sieve.core.filter_base import ALL_FRAMES
from sieve.core.types import ChannelSpec, Frame
from sieve.filters.span import SpanParams, span_cpu


def frame_at(index: int) -> Frame:
    """A frame whose pixels say which frame it is."""
    return Frame(
        data=np.full((4, 4), index % 256, dtype=np.uint8), index=index, channels=ChannelSpec.GRAY
    )


def test_the_identity_span_keeps_every_frame_there_could_be() -> None:
    # What "no span" is spelled as. The end is past any footage rather than the
    # video's own length, because the graph is written by things that have not
    # opened it — the schema-v6 upgrade validator and a hand-typed YAML.
    assert SpanParams().selected_frames() == ALL_FRAMES
    assert SpanParams(start=10, end=14).selected_frames() == range(10, 14)


def test_the_identity_span_is_a_value_in_the_saved_params() -> None:
    # REWORK.md R1: no `X | None` reaches the plan, so the default has to survive
    # to the cache key as a range rather than as an absence. A field that
    # serialized to null would take this with it, and the plan's fold would then
    # need a branch for "this node selects nothing" that means the opposite of
    # "this node selects no frames".
    assert SpanParams().canonical_json() == '{"end":4294967296,"start":0}'
    assert SpanParams.model_validate_json(SpanParams().model_dump_json()) == SpanParams()


def test_the_kernel_passes_a_lead_in_frame_through_rather_than_refusing_it() -> None:
    # The design, stated where it looks most like an oversight. Frames below
    # `start` reach this kernel by construction — `decode_range` widens the span
    # by the graph's lead-in — and they are what warms everything downstream
    # before the executor discards them at the yield. A kernel that refused them
    # would make a span node behind any settling filter unrunnable, and one that
    # dropped them would leave that filter unsettled for the entire answer.
    params = SpanParams(start=10, end=14)

    early, inside = span_cpu(frame_at(7), params), span_cpu(frame_at(11), params)

    assert (early.index, inside.index) == (7, 11)
    assert np.array_equal(early.data, frame_at(7).data)
    assert np.array_equal(inside.data, frame_at(11).data)


def test_an_empty_or_backwards_range_is_refused_at_the_node() -> None:
    # Refused here rather than folded into an empty intersection in
    # `plan._selected`, because they are different mistakes: two ranges that
    # each make sense and do not overlap needs both named, and one range that
    # makes no sense needs only the node.
    with pytest.raises(ValidationError, match="at least one frame"):
        SpanParams(start=14, end=10)
    with pytest.raises(ValidationError, match="at least one frame"):
        SpanParams(start=10, end=10)
    with pytest.raises(ValidationError, match="non-negative"):
        SpanParams(start=-1, end=10)
