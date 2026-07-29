








from __future__ import annotations

import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline
from sieve.gui.chain_model import Status, grade, parity_chain
from sieve.gui.wizard_model import (
    BREAKS_BELOW,
    IN_CHAIN,
    candidates_for_insert,
    candidates_for_swap,
    catalog,
    chain_from_pipeline,
    guidance_for,
    insert_step,
    swap_step,
)


def _entry(entry_id: str):
    return next(e for e in catalog() if e.entry_id == entry_id)


def test_the_two_disable_rules_name_their_reasons() -> None:






    chain = parity_chain(30.0)

    at_top = {c.entry.entry_id: c for c in candidates_for_insert(chain, 0)}
    assert not at_top["normalize"].enabled
    assert at_top["normalize"].reason == IN_CHAIN


    assert "morlet_band" not in at_top



    headless = chain.without("block_signal")
    offers = {c.entry.entry_id: c for c in candidates_for_insert(headless, 0)}
    assert not offers["block_signal"].enabled
    assert offers["block_signal"].reason == BREAKS_BELOW


def test_an_enabled_offer_grades_conflict_free_and_wires_chain_state() -> None:






    chain = parity_chain(20.0, scale=0.5)
    removed = chain.without("block_signal")
    seam = next(i for i, s in enumerate(removed.steps) if s.step_id == "morlet_band")

    offer = next(
        c for c in candidates_for_insert(removed, seam) if c.entry.entry_id == "block_signal"
    )
    assert offer.enabled

    repaired, step_id = insert_step(removed, seam, offer.entry)
    assert all(g.status is Status.OK for g in grade(repaired.steps))
    node = next(s for s in repaired.steps if s.step_id == step_id).node
    assert node is not None
    assert node.params["fps"] == 20.0
    assert node.params["scale"] == 0.5


def test_swap_exempts_the_replaced_step_and_keeps_its_params() -> None:

    chain = parity_chain(30.0)
    tuned, _ = swap_step(chain, "rescale", _entry("rescale"), params={"scale": 0.25})

    offers = {c.entry.entry_id: c for c in candidates_for_swap(tuned, "rescale")}
    assert offers["rescale"].enabled

    same, step_id = swap_step(tuned, "rescale", _entry("rescale"))
    node = next(s for s in same.steps if s.step_id == step_id).node
    assert node is not None and node.params["scale"] == 0.25


def test_guidance_comes_from_the_shipped_markdown() -> None:

    guidance = guidance_for(_entry("rescale"))
    assert "crop" in guidance.not_do
    assert guidance.when_to_use and guidance.cost
    assert guidance.summary


def test_chain_from_pipeline_inverts_runnable_prefix_keeping_node_identity() -> None:






    saved = parity_chain(30.0).pipeline()

    rebuilt = chain_from_pipeline(saved, 30.0)

    assert rebuilt.pipeline() == saved
    assert [s.step_id for s in rebuilt.steps] == [
        "rescale",
        "normalize",
        "block_signal",
        "morlet_band",
        "windowed_count",
    ]
    assert [s.node.node_id for s in rebuilt.steps if s.node is not None] == [
        n.node_id for n in saved.nodes
    ]


def test_chain_from_pipeline_refuses_what_the_stack_cannot_host() -> None:

    a = Node(filter_id="rescale", version="1.0.0")
    b = Node(filter_id="normalize", version="1.0.0")
    c = Node(filter_id="block_signal", version="1.0.0")
    branching = Pipeline(
        nodes=(a, b, c),
        edges=(
            Edge(upstream=a.node_id, downstream=b.node_id),
            Edge(upstream=a.node_id, downstream=c.node_id, port="b"),
        ),
    )
    with pytest.raises(ValueError, match="branches"):
        chain_from_pipeline(branching, 30.0)

    unknown = Pipeline(nodes=(Node(filter_id="mystery", version="1.0.0"),))
    with pytest.raises(ValueError, match="mystery"):
        chain_from_pipeline(unknown, 30.0)
