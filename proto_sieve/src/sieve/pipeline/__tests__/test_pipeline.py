"""Proof for pipeline.py's secret (chunk 6, previously REPL-verified only —
see docs/STATUS.md): a pipeline round-trips through JSON, and lowering it
produces the same graph a hand-built one would.
"""

from __future__ import annotations

from proto_sieve.src.sieve.kernel import Affine, Node, Slice, Source, recipe_hash
from proto_sieve.src.sieve.pipeline import Pipeline, Step, from_json, lower, to_json


def _pipeline() -> Pipeline:
    return Pipeline(
        source="rep3_intermittent_crop",
        steps=(Step(tool="crop", params={"y0": 0, "y1": 200, "x0": 0, "x1": 200}),),
    )


def test_json_round_trip_preserves_the_value():
    pipeline = _pipeline()
    assert from_json(to_json(pipeline)) == pipeline


def test_lower_produces_the_same_hash_as_a_hand_built_graph():
    hand_built = Node(Slice(0, 200, 0, 200), (Node(Source("rep3_intermittent_crop")),))
    assert recipe_hash(lower(_pipeline())) == recipe_hash(hand_built)
