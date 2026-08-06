"""The wizard model's load-bearing claims.

The wizard cannot break the chain — so what matters is exactly the judging:
a duplicate reads "in chain", a kind-breaker reads "breaks below", an enabled
offer really does leave the chain conflict-free, and the repair path back to
a removed suffix step exists. Guidance parsing is pinned against a shipped
`.md`, because the pane renders real files, not fixtures.
"""

from __future__ import annotations

import pytest

from sieve.core.filter_base import (
    ArraySpec,
    AuthoringGroup,
    CostEstimate,
    ElementRelation,
    ParamsBase,
)
from sieve.core.filter_registry import FilterRegistry, register_filter
from sieve.core.pipeline_model import Edge, Node, Pipeline
from sieve.core.types import WorkUnits
from sieve.filters import discover
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
from sieve.pipeline.dag import Dag

SYNTHETIC_FILTER_ID = "synthetic_smooth"
SYNTHETIC_VERSION = "1.0.0"
SYNTHETIC_COST = CostEstimate(work_per_megapixel=WorkUnits(1.0))


def _entry(entry_id: str):
    return next(e for e in catalog() if e.entry_id == entry_id)


def _registry_with_synthetic_filter() -> FilterRegistry:
    registry = FilterRegistry()
    for spec in discover():
        registry.register(spec)

    @register_filter(
        filter_id=SYNTHETIC_FILTER_ID,
        version=SYNTHETIC_VERSION,
        summary="A test-only image smoother.",
        accepts=ArraySpec(),
        emits=ArraySpec(),
        element=ElementRelation.PRESERVED,
        cost=SYNTHETIC_COST,
        authoring_group=AuthoringGroup.SPATIAL_PREP,
        registry=registry,
    )
    class SyntheticSmoothParams(ParamsBase):
        strength: int = 2

    assert SyntheticSmoothParams.spec().filter_id == SYNTHETIC_FILTER_ID
    return registry


def test_the_two_disable_rules_name_their_reasons() -> None:
    """A duplicate is "in chain"; a fitting kind-breaker is "breaks below".

    Both are listed rather than hidden — the catalogue must not feel
    dishonest — and both are refused with the reason the mockup pinned. An
    entry whose input kind does not match the seam at all is simply absent.
    """
    chain = parity_chain(30.0)

    at_top = {c.entry.entry_id: c for c in candidates_for_insert(chain, 0)}
    assert not at_top["normalize"].enabled
    assert at_top["normalize"].reason == IN_CHAIN
    # The suffix steps take block series; the top of the chain carries an
    # image, so they are not offers there at all.
    assert "morlet_band" not in at_top

    # With the extraction step gone, re-inserting it at the top would fit the
    # seam (image in) and break rescale below (block series out).
    headless = chain.without("block_signal")
    offers = {c.entry.entry_id: c for c in candidates_for_insert(headless, 0)}
    assert not offers["block_signal"].enabled
    assert offers["block_signal"].reason == BREAKS_BELOW


def test_an_enabled_offer_grades_conflict_free_and_wires_chain_state() -> None:
    """Enabled means the hypothetical chain runs, with chain state injected.

    `block_signal`'s node must carry the chain's fps and the rescale step's
    scale — the parity wiring — not the params model's defaults, or the
    committed step would extract against a grid the knobs disagree with.
    """
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


def test_registered_filter_appears_in_authoring_without_catalog_edit() -> None:
    """A filter registered only in a scratch shelf is still offered."""
    registry = _registry_with_synthetic_filter()
    chain = parity_chain(30.0)

    graph_offers = Dag.attachable_operations(ArraySpec(), registry=registry)
    assert SYNTHETIC_FILTER_ID in {offer.spec.filter_id for offer in graph_offers}

    candidates = {
        c.entry.entry_id: c for c in candidates_for_insert(chain, 0, registry=registry)
    }
    offer = candidates[SYNTHETIC_FILTER_ID]
    assert offer.enabled
    assert offer.entry.title == "Synthetic smooth"

    proposed, step_id = insert_step(chain, 0, offer.entry, registry=registry)
    inserted = proposed.steps[0]
    assert step_id == SYNTHETIC_FILTER_ID
    assert inserted.node is not None
    assert inserted.node.filter_id == SYNTHETIC_FILTER_ID
    assert inserted.node.params == {"strength": 2}
    assert all(each.status is Status.OK for each in grade(proposed.steps))


def test_chain_from_pipeline_renders_registered_filter_without_catalog_edit() -> None:
    """Loading a graph resolves the same scratch-registered catalog entry."""
    registry = _registry_with_synthetic_filter()
    synthetic = Node(
        node_id="smooth",
        filter_id=SYNTHETIC_FILTER_ID,
        version=SYNTHETIC_VERSION,
        params={"strength": 4},
    )
    block_signal = Node(
        node_id="signal",
        filter_id="block_signal",
        version="1.0.0",
        params={"signal": "change_energy", "block": 0, "scale": 1.0, "fps": 30.0},
    )
    saved = Pipeline(
        nodes=(synthetic, block_signal),
        edges=(Edge(upstream=synthetic.node_id, downstream=block_signal.node_id),),
    )

    rebuilt = chain_from_pipeline(saved, 30.0, registry=registry)

    assert rebuilt.pipeline() == saved
    assert [s.step_id for s in rebuilt.steps] == [
        SYNTHETIC_FILTER_ID,
        "block_signal",
        "morlet_band",
        "windowed_count",
    ]
    assert [s.node.node_id for s in rebuilt.steps if s.node is not None] == [
        "smooth",
        "signal",
    ]


def test_swap_exempts_the_replaced_step_and_keeps_its_params() -> None:
    """The wizard doubles as a settings surface: same entry back, params kept."""
    chain = parity_chain(30.0)
    tuned, _ = swap_step(chain, "rescale", _entry("rescale"), params={"scale": 0.25})

    offers = {c.entry.entry_id: c for c in candidates_for_swap(tuned, "rescale")}
    assert offers["rescale"].enabled  # not "in chain" — it is the step being replaced

    same, step_id = swap_step(tuned, "rescale", _entry("rescale"))
    node = next(s for s in same.steps if s.step_id == step_id).node
    assert node is not None and node.params["scale"] == 0.25


def test_guidance_comes_from_the_shipped_markdown() -> None:
    """The pane renders the filter's real `.md` sections, not a placeholder."""
    guidance = guidance_for(_entry("rescale"))
    assert "crop" in guidance.not_do
    assert guidance.when_to_use and guidance.cost
    assert guidance.summary  # the registered spec's one-liner


def test_chain_from_pipeline_inverts_runnable_prefix_keeping_node_identity() -> None:
    """A saved graph regrows the stack it came from, ids intact, suffix restored.

    Identity is the load-bearing half: replicate overrides pin against node
    ids and cache entries key on them, so a reconstruction that reminted ids
    would orphan every pin a project was saved with.
    """
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
    """A branching graph and an unknown filter are refused, not approximated."""
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
