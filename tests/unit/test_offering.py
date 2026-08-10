"""What may be offered for a position, which is not what an edge may carry.

Every case here is a pair: the same two specs put to `admits` and to `matches`,
so the dual is asserted rather than described. `admits` is false only on proven
disjointness and `matches` true only on proven compatibility, which means the
interesting inputs are the ones in between — a partial overlap, an unresolved
producer — where both answer yes and no respectively, and a predicate that had
quietly become one function would go red on every one of them.

A wildcard is no longer one of those inputs on the *required* side:
`adr/an-unstated-field-is-a-claim.md` rules an unstated `accepts` field a
declared universal, so the case that used to assert `ArraySpec().matches` false
is gone and `test_an_unstated_accepts_field_is_offered_where_the_stated_fields_fit`
stands where it did. The produced side is untouched — ignorance about what a
position emits is still never plausible — which is what keeps the two predicates
apart.

The shelf here is scratch (`test_dag.py`'s reason: the process-wide registry is
filled by tool imports, and a test registering into it would depend on whether
one had happened yet).
"""

from __future__ import annotations

import pytest

from sieve.core.tool_base import (
    ArraySpec,
    ElementKind,
    ElementNames,
    ElementRelation,
    Emission,
    ParamsBase,
    TableSpec,
    ToolSpec,
)
from sieve.core.tool_registry import ToolRegistry, offered_tools, register_tool
from sieve.core.types import ChannelSpec

SHELF = ToolRegistry()

GRAY_FLOAT = ArraySpec(dtypes=("float32",), channels=(ChannelSpec.GRAY,))
ANY_FLOAT = ArraySpec(dtypes=("uint8", "float32"), channels=(ChannelSpec.GRAY, ChannelSpec.BGR))


def _spec(
    tool_id: str,
    accepts: ArraySpec | TableSpec,
    element: ElementKind | ElementRelation | None = ElementRelation.PRESERVED,
) -> ToolSpec:
    @register_tool(
        tool_id=tool_id,
        version="1.0.0",
        summary="Scratch.",
        accepts=accepts,
        emits=TableSpec(columns=("x", "y")) if element is None else GRAY_FLOAT,
        emissions=(Emission("out"),),
        element=element,
        element_names=ElementNames("thing", "things") if isinstance(element, ElementKind) else None,
        registry=SHELF,
    )
    class Params(ParamsBase):
        pass

    return Params.spec()


NARROW = _spec("narrow", GRAY_FLOAT)
WIDE = _spec("wide", ANY_FLOAT)
WILDCARD = _spec("wildcard", ArraySpec())
AGGREGATOR = _spec("aggregator", GRAY_FLOAT, element=ElementRelation.AGGREGATED)
TABULATOR = _spec("tabulator", TableSpec(columns=("x", "y")), element=None)


def test_offering_refuses_the_wildcard_producer_that_admits() -> None:
    assert GRAY_FLOAT.admits(ArraySpec())
    assert not GRAY_FLOAT.matches(ArraySpec())


def test_offering_refuses_the_half_declared_producer_that_admits() -> None:
    produced = ArraySpec(dtypes=("float32",))

    assert GRAY_FLOAT.admits(produced)
    assert not GRAY_FLOAT.matches(produced)


def test_offering_refuses_the_partial_overlap_that_admits() -> None:
    produced = ArraySpec(dtypes=("uint8", "float32"), channels=(ChannelSpec.GRAY,))

    assert GRAY_FLOAT.admits(produced)
    assert not GRAY_FLOAT.matches(produced)


def test_offering_matches_a_producer_the_accept_covers() -> None:
    assert ANY_FLOAT.matches(GRAY_FLOAT)
    assert GRAY_FLOAT.matches(GRAY_FLOAT)


def test_offering_refuses_a_kind_mismatch_as_admits_does() -> None:
    table = TableSpec(columns=("x", "y"))

    assert not GRAY_FLOAT.admits(table)
    assert not GRAY_FLOAT.matches(table)
    assert not table.admits(GRAY_FLOAT)
    assert not table.matches(GRAY_FLOAT)


def test_offering_matches_a_table_whose_required_columns_are_all_produced() -> None:
    accepts = TableSpec(columns=("x", "y"))

    assert accepts.matches(TableSpec(columns=("x", "y", "frame")))
    assert not accepts.matches(TableSpec(columns=("x",)))
    # A table nobody has resolved is still unproven, and a reader naming no
    # column at all still takes any table there is — the two sides of ADR 32 on
    # the third field it rules over.
    assert not accepts.matches(TableSpec())
    assert TableSpec().matches(TableSpec(columns=("x", "y")))


def test_offering_slack_counts_what_the_accept_tolerates_and_did_not_get() -> None:
    assert GRAY_FLOAT.match_slack(GRAY_FLOAT) == (0, 0)
    # One dtype and one channel the wide accept allows and this position never
    # produces.
    assert ANY_FLOAT.match_slack(GRAY_FLOAT) == (0, 2)
    assert GRAY_FLOAT.match_slack(ArraySpec()) is None
    assert TableSpec(columns=("x",)).match_slack(TableSpec(columns=("x", "y"))) == (0, 1)


def test_an_unstated_accepts_field_is_offered_where_the_stated_fields_fit() -> None:
    """ADR 32: an empty `accepts` field is a tool declaring it takes anything.

    A predicate that read it as unproven refused that tool at *every* position
    rather than at one, which is a constant and not a shortlist — twelve of
    fourteen on the shelf, measured in the finding this item's fold moved.
    """
    half = ArraySpec(dtypes=("float32",))

    assert ArraySpec().matches(GRAY_FLOAT)
    assert half.matches(GRAY_FLOAT)
    # Stated fields still bind: the wildcard is on the channel axis alone.
    assert not half.matches(ArraySpec(dtypes=("uint8",), channels=(ChannelSpec.GRAY,)))
    # And the produced side is unchanged — ignorance about what a position
    # emits is still never plausible.
    assert not ArraySpec().matches(ArraySpec())


def test_an_unstated_accepts_field_sorts_behind_every_stated_one() -> None:
    half = ArraySpec(dtypes=("float32",))

    assert ArraySpec().match_slack(GRAY_FLOAT) == (2, 0)
    assert half.match_slack(GRAY_FLOAT) == (1, 0)

    # Lexicographic, and this is the pair that makes it more than a sum: one
    # wildcard field tolerates every value there will ever be, so it is looser
    # than two named members the position happens not to produce, and a plain
    # count would have put it first.
    assert half.match_slack(GRAY_FLOAT) > ANY_FLOAT.match_slack(GRAY_FLOAT)


def test_offering_orders_the_tighter_accept_first() -> None:
    offered = offered_tools(GRAY_FLOAT, ElementKind.PIXEL, SHELF)

    # `narrow` and `aggregator` declare the same accept, so they tie on slack
    # and fall to the id — the order is the declarations' and never the
    # registration's. `wildcard` takes anything and so fits least.
    assert [spec.tool_id for spec in offered] == ["aggregator", "narrow", "wide", "wildcard"]


def test_offering_drops_the_tool_whose_elements_would_lose_their_meaning() -> None:
    over_pixels = offered_tools(GRAY_FLOAT, ElementKind.PIXEL, SHELF)
    over_blocks = offered_tools(GRAY_FLOAT, ElementKind.BLOCK, SHELF)

    assert "aggregator" in [spec.tool_id for spec in over_pixels]
    assert "aggregator" not in [spec.tool_id for spec in over_blocks]
    assert "narrow" in [spec.tool_id for spec in over_blocks]


def test_offering_without_an_element_refuses_nothing_the_element_leg_would() -> None:
    # `None` is every position downstream of an aggregator over blocks —
    # `node_element` never recovers it — and the leg that refuses an aggregator
    # over blocks has nothing to say there: the noun was lost upstream, so no
    # tool here can lose it.
    lost_the_noun = offered_tools(GRAY_FLOAT, None, SHELF)

    assert [spec.tool_id for spec in lost_the_noun] == ["aggregator", "narrow", "wide", "wildcard"]
    assert lost_the_noun == offered_tools(GRAY_FLOAT, ElementKind.PIXEL, SHELF)


def test_offering_keeps_the_table_reader_that_declares_no_elements() -> None:
    offered = offered_tools(TableSpec(columns=("x", "y", "frame")), None, SHELF)

    assert [spec.tool_id for spec in offered] == ["tabulator"]


def test_offering_is_empty_where_nothing_is_proven_rather_than_being_the_shelf() -> None:
    admitting = [spec for spec in SHELF if spec.accepts.admits(ArraySpec())]

    assert len(admitting) > 1
    assert offered_tools(ArraySpec(), ElementKind.PIXEL, SHELF) == ()


@pytest.mark.parametrize("element", [ElementKind.PIXEL, ElementKind.BLOCK, ElementKind.FRAME])
def test_offering_never_offers_what_the_edge_check_would_reject(element: ElementKind) -> None:
    produced = ArraySpec(dtypes=("float32",), channels=(ChannelSpec.GRAY,))

    for spec in offered_tools(produced, element, SHELF):
        assert spec.accepts.admits(produced)
