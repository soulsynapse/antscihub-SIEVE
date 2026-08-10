"""The first tool with two inputs, and the two things only two inputs can fail.

The kernel half is that the ports are read *by name*: a merging run is handed a
mapping rather than a pair, so nothing in it may depend on which key the executor
assembled first. The graph half is `todo/a-merge-keys-its-inputs-by-port.md`'s
claim run against a shipped tool for the first time — a document and its
port-swapped twin are two computations — where `test_cache_key.py` runs it over a
spec declared against a scratch registry.

The shape refusal is here because numpy would not raise it. A block grid and a
frame of pixels broadcast against each other whenever one axis happens to be 1,
and the difference that comes out is a full-size array nothing downstream could
tell from a real one.
"""

from __future__ import annotations

import numpy as np
import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline
from sieve.core.types import ChannelSpec, Frame, FrameSpan
from sieve.pipeline.dag import Dag
from sieve.tools import discover
from sieve.tools.subtract import MINUEND, SUBTRAHEND, SubtractMode, SubtractParams
from sieve.tools.subtract import run as subtract_run

SPEC = SubtractParams.spec()

SOURCE = "footage|1|2"

HEIGHT, WIDTH = 4, 5


def frame(seed: int, *, shape: tuple[int, ...] = (HEIGHT, WIDTH)) -> Frame:
    rng = np.random.default_rng(seed)
    return Frame(data=rng.random(shape).astype(np.float32), index=0, channels=ChannelSpec.GRAY)


def window(minuend: Frame, subtrahend: Frame) -> dict[str, FrameSpan]:
    """The port-keyed form `ToolRun` takes, built in the order that hides bugs.

    Reverse-sorted keys, so a run reading the mapping positionally — by
    insertion, by `next(iter(...))` — gets the wrong operand and the sign of
    every case below flips.
    """
    return {SUBTRAHEND: FrameSpan((subtrahend,)), MINUEND: FrameSpan((minuend,))}


class TestPorts:
    def test_two_inputs_arrive_on_named_ports(self) -> None:
        # Both halves of "named": the declaration says which two names exist,
        # and the run answers to them rather than to an order. Signed, because
        # the default is the setting under which the two ports are not
        # interchangeable — `MAGNITUDE` would pass this with the operands
        # swapped and prove only that a difference was taken.
        plate, background = frame(1), frame(2)

        assert set(SPEC.input_ports) == {MINUEND, SUBTRAHEND}

        produced = subtract_run(SubtractParams(), window(plate, background), None)
        crossed = subtract_run(SubtractParams(), window(background, plate), None)

        np.testing.assert_allclose(produced.data, plate.data - background.data)
        np.testing.assert_allclose(crossed.data, -(plate.data - background.data))

    def test_magnitude_discards_the_polarity_the_wiring_chose(self) -> None:
        # The setting that makes the two ports interchangeable, which is what a
        # detector reading either direction of departure asks for. It is the
        # tool's one parameter and the only thing that can make the case above
        # stop distinguishing the ports, so it is pinned rather than inferred
        # from the enum's existence.
        plate, background = frame(3), frame(4)
        params = SubtractParams(mode=SubtractMode.MAGNITUDE)

        produced = subtract_run(params, window(plate, background), None)
        crossed = subtract_run(params, window(background, plate), None)

        np.testing.assert_allclose(produced.data, np.abs(plate.data - background.data))
        np.testing.assert_allclose(crossed.data, produced.data)

    def test_two_geometries_are_refused_rather_than_broadcast(self) -> None:
        # `(4, 5)` against `(4, 1)` is the pair numpy is happiest to accept: it
        # broadcasts to a full-size difference of a frame against one column of
        # itself, which is a picture rather than an error.
        with pytest.raises(ValueError, match="one subtraction is one geometry"):
            subtract_run(SubtractParams(), window(frame(5), frame(6, shape=(HEIGHT, 1))), None)


class TestWiring:
    def test_a_crossed_pair_is_not_the_same_graph(self) -> None:
        # The claim deferred since 2026-08-07 for want of a subject, run for the
        # first time over a shipped tool and a saved document rather than a spec
        # a test declared. The two branches must key differently, or the crossed
        # pairs would be equal whatever the digest did with the ports.
        discover()

        def keys(minuend: str, subtrahend: str) -> dict[str, str]:
            pipeline = Pipeline(
                nodes=(
                    Node(node_id="p", tool_id="normalize", version="1.0.0", params={"mode": "off"}),
                    Node(
                        node_id="q",
                        tool_id="normalize",
                        version="1.0.0",
                        params={"mode": "zscore"},
                    ),
                    Node(node_id="m", tool_id="subtract", version="1.0.0"),
                ),
                edges=(
                    Edge(upstream=minuend, downstream="m", port=MINUEND),
                    Edge(upstream=subtrahend, downstream="m", port=SUBTRAHEND),
                ),
            )
            return Dag.build(pipeline).node_keys(source=SOURCE)

        straight = keys("p", "q")
        crossed = keys("q", "p")

        assert straight["m"] != crossed["m"]
        assert {node: key for node, key in straight.items() if node != "m"} == {
            node: key for node, key in crossed.items() if node != "m"
        }
