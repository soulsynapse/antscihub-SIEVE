"""The wizard model's load-bearing claims.

The wizard cannot break the chain — so what matters is exactly the judging:
a duplicate reads "in chain", a kind-breaker reads "breaks below", an enabled
offer really does leave the chain conflict-free, and the repair path back to
a removed suffix step exists. Guidance parsing is pinned against a shipped
`.md`, because the pane renders real files, not fixtures.
"""

from __future__ import annotations

from sieve.gui.chain_model import Status, grade, parity_chain
from sieve.gui.wizard_model import (
    BREAKS_BELOW,
    IN_CHAIN,
    candidates_for_insert,
    candidates_for_swap,
    catalog,
    guidance_for,
    insert_step,
    swap_step,
)


def _entry(entry_id: str):
    return next(e for e in catalog() if e.entry_id == entry_id)


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
