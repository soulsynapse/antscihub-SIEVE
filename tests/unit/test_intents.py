"""Every mutation of the open project, entering as one intent.

Each case here stands in for a way the layer stops being the document's only
writer, or stops being keyed by *what was mutated* rather than by what emitted
it: a value that lands somewhere the undo stack cannot reach, an override that
needs a kind of its own, a checkoff that moves a cache key, or a refused intent
that pushes a value anyway.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from sieve.core.pipeline_model import (
    Edge,
    Node,
    Pipeline,
    Project,
    Replicate,
    Sink,
    SourceRef,
)
from sieve.core.tool_base import (
    ArraySpec,
    ElementRelation,
    Emission,
    ParamsBase,
    ParamStereotype,
    ToolSpec,
)
from sieve.pipeline.cache_key import node_key
from sieve.session import intents
from sieve.session.intents import (
    INTENT_KINDS,
    AddNode,
    AddReplicate,
    Intent,
    RemoveNode,
    RemoveReplicate,
    RetoolNode,
    SetOutputs,
    SetParam,
    intent_kinds,
    issue,
)
from sieve.session.session import Session


class ThresholdParams(ParamsBase):
    """Two fields, so an edit to one can leave the other where it was."""

    level: float = 0.25
    smoothing: int = 1


SPEC = ToolSpec(
    tool_id="threshold",
    version="1.0.0",
    summary="Threshold.",
    params_model=ThresholdParams,
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    element=ElementRelation.PRESERVED,
    param_stereotypes={
        "level": ParamStereotype.SCALAR_RANGE,
        "smoothing": ParamStereotype.SCALAR_RANGE,
    },
)

#: Stands in for whatever the walk hands a root — in schema v1 that is the
#: source key, and nothing here is asking what it is.
ROOT = "root-key"


def _project(*replicates: Replicate) -> Project:
    return Project(
        source=SourceRef(path="arena.MP4"),
        replicates=replicates,
        pipeline=Pipeline(
            nodes=(
                Node(node_id="n1", tool_id="threshold", version="1.0.0", params={"level": 0.25}),
            )
        ),
    )


def _opened(tmp_path: Path, *replicates: Replicate) -> Session:
    path = tmp_path / "arena.sieve.yaml"
    _project(*replicates).save(path)
    return Session.open(path)


def _key(project: Project, replicate: Replicate | None = None) -> str:
    return node_key(project.pipeline.node("n1"), spec=SPEC, upstream=ROOT, replicate=replicate)


#: Typed out by hand, which is the whole of its job: `INTENT_KINDS` derives
#: itself from the module, so the only thing that can notice a kind arriving or
#: leaving is a list written somewhere the module cannot reach. VISION's
#: reshuffle scenario reads this set as the bindings a complete GUI must emit,
#: so an eighth name below is a claim about what a layout now owes.
KIND_NAMES = {
    "SetParam",
    "SetOutputs",
    "RemoveNode",
    "AddNode",
    "AddReplicate",
    "RemoveReplicate",
    "RetoolNode",
}


@dataclass(frozen=True, slots=True)
class Reframe:
    """An eighth kind, of the shape a later phase would add one in."""

    node_id: str

    def applied_to(self, project: Project) -> Project:
        return project


def test_the_kinds_are_the_modules_own() -> None:
    # The classes the rest of this file issues, not names beside them: a tuple
    # of strings would let the enumeration and the module drift while both still
    # read correctly, which is the defect this list was minted against.
    assert set(INTENT_KINDS) == {
        SetParam,
        SetOutputs,
        RemoveNode,
        AddNode,
        AddReplicate,
        RemoveReplicate,
        RetoolNode,
    }
    assert {kind.__name__ for kind in INTENT_KINDS} == KIND_NAMES
    assert all(issubclass(kind, Intent) for kind in INTENT_KINDS)


def test_a_new_kind_fails_the_list() -> None:
    # A kind arriving is not something the module can hide: the derivation picks
    # up anything intent-shaped, so the eighth joins without an edit...
    grown = intent_kinds({"Reframe": Reframe, **vars(intents)})
    assert Reframe in grown

    # ...and the hand-typed set above is what then goes red, which is the half
    # that makes the enumeration worth having. Without this, a phase could add a
    # surface, emit a kind nothing binds, and leave VISION's completeness claim
    # true of a shorter list than the one the app has.
    assert {kind.__name__ for kind in grown} != KIND_NAMES


def test_a_set_param_intent_lands_as_a_new_whole_value(tmp_path: Path) -> None:
    session = _opened(tmp_path)
    before = session.project

    issue(session, SetParam(node_id="n1", param="level", value=0.5))

    assert session.project.params_for("n1") == {"level": 0.5}
    assert before.params_for("n1") == {"level": 0.25}
    assert session.undo() == before


def test_an_override_is_the_same_kind_at_a_longer_address(tmp_path: Path) -> None:
    dish = Replicate(name="dish", replicate_id="r1")
    session = _opened(tmp_path, dish)

    issue(session, SetParam(node_id="n1", param="level", value=0.5, replicate_id="r1"))

    assert session.project.params_for("n1", "r1") == {"level": 0.5}
    assert session.project.replicate("r1").override_for("n1") == {"level": 0.5}


def test_set_outputs_moves_no_cache_key(tmp_path: Path) -> None:
    session = _opened(tmp_path)
    before = _key(session.project)

    issue(
        session,
        SetOutputs(
            checkpoints=("n1",),
            outputs=(Sink(sink_id="s1", node_id="n1", format="npy", path="out"),),
        ),
    )

    assert session.project.checkpoints == ("n1",)
    assert len(session.project.outputs) == 1
    assert _key(session.project) == before


def test_removing_a_node_is_a_whole_value_like_any_other_edit(tmp_path: Path) -> None:
    path = tmp_path / "arena.sieve.yaml"
    Project(
        source=SourceRef(path="arena.MP4"),
        pipeline=Pipeline(
            nodes=tuple(
                Node(node_id=node_id, tool_id="threshold", version="1.0.0")
                for node_id in ("n1", "n2", "n3")
            ),
            edges=(Edge(upstream="n1", downstream="n2"), Edge(upstream="n2", downstream="n3")),
        ),
    ).save(path)
    session = Session.open(path)
    before = session.project

    issue(session, RemoveNode(node_id="n2"))

    # A structural edit lands the same way a parameter does — one new document
    # on the stack — which is what keeps the session ignorant of what an edit
    # was. Undo does not have to know how to put a node back.
    pipeline = session.project.pipeline
    assert [node.node_id for node in pipeline.nodes] == ["n1", "n3"]
    assert [(edge.upstream, edge.downstream) for edge in pipeline.edges] == [("n1", "n3")]
    assert session.undo() == before


def test_adding_a_node_splices_it_and_undoes_as_one_value(tmp_path: Path) -> None:
    path = tmp_path / "arena.sieve.yaml"
    Project(
        source=SourceRef(path="arena.MP4"),
        checkpoints=("n1",),
        pipeline=Pipeline(
            nodes=tuple(
                Node(node_id=node_id, tool_id="threshold", version="1.0.0")
                for node_id in ("n1", "n2")
            ),
            edges=(Edge(upstream="n1", downstream="n2"),),
        ),
    ).save(path)
    session = Session.open(path)
    before = session.project

    issue(
        session,
        AddNode(site_id="n1", node=Node(node_id="n3", tool_id="threshold", version="1.0.0")),
    )

    pipeline = session.project.pipeline
    assert [(edge.upstream, edge.downstream) for edge in pipeline.edges] == [
        ("n3", "n2"),
        ("n1", "n3"),
    ]
    # An arriving node is named by nothing the document holds beside the graph,
    # which is the asymmetry with `RemoveNode`: no checkpoint, sink, override or
    # input hash is touched, so the splice is `with_pipeline` and nothing else.
    assert session.project.checkpoints == ("n1",)
    assert session.undo() == before


def test_retooling_a_node_keeps_the_node_and_undoes_as_one_value(tmp_path: Path) -> None:
    path = tmp_path / "arena.sieve.yaml"
    Project(
        source=SourceRef(path="arena.MP4"),
        checkpoints=("n2",),
        outputs=(Sink(sink_id="s1", node_id="n2", format="csv", path="out"),),
        pipeline=Pipeline(
            nodes=(
                Node(node_id="n1", tool_id="threshold", version="1.0.0"),
                Node(node_id="n2", tool_id="threshold", version="1.0.0", params={"level": 0.9}),
            ),
            edges=(Edge(upstream="n1", downstream="n2"),),
        ),
    ).save(path)
    session = Session.open(path)
    before = session.project

    issue(session, RetoolNode(node_id="n2", tool_id="blur", version="2.0.0"))

    # The third kind, and what makes it one rather than a `RemoveNode` and an
    # `AddNode`: the pair would mint a name, and `node_id` is what the
    # checkpoint, the sink and the artifact on disk are addressed by.
    project = session.project
    assert [(node.node_id, node.tool_id) for node in project.pipeline.nodes] == [
        ("n1", "threshold"),
        ("n2", "blur"),
    ]
    assert project.checkpoints == ("n2",)
    assert [sink.node_id for sink in project.outputs] == ["n2"]
    assert project.pipeline.node("n2").params == {}
    assert session.undo() == before


def test_a_region_arrives_at_the_foot_carrying_its_own_deviation(tmp_path: Path) -> None:
    first = Replicate(name="north", overrides={"n1": {"level": 0.4}})
    session = _opened(tmp_path, first)
    before = session.project

    issue(
        session,
        AddReplicate(Replicate(name="south", overrides={"n1": {"level": 0.4}})),
    )

    # At the foot, because the order is the one per-replicate outputs are
    # written in and the fan draws ordinals off it — an insertion beside its
    # sibling would renumber every region after it.
    project = session.project
    assert [replicate.name for replicate in project.replicates] == ["north", "south"]
    # And carrying a deviation of its own rather than following: the baseline is
    # what the next edit to *either* region moves, so an unpinned arrival would
    # be dragged along by the edit that placed the one beside it.
    assert project.params_for("n1", project.replicates[1].replicate_id) == {"level": 0.4}
    assert session.undo() == before
    assert session.project.replicates == (first,)


def test_dropping_the_last_region_is_the_baseline_again(tmp_path: Path) -> None:
    session = _opened(tmp_path, Replicate(name="north", overrides={"n1": {"level": 0.4}}))
    before = session.project

    issue(session, RemoveReplicate(session.project.replicates[0].replicate_id))

    # Nothing refuses it. A project with no replicates runs the node's baseline
    # once, which is the state every document is minted in — a floor here would
    # make the first region a gesture with no way back.
    assert session.project.replicates == ()
    assert session.project.params_for("n1") == {"level": 0.25}
    assert session.undo() == before


def test_an_intent_naming_no_node_leaves_the_session_where_it_was(tmp_path: Path) -> None:
    session = _opened(tmp_path)

    with pytest.raises(KeyError):
        issue(session, SetParam(node_id="nowhere", param="level", value=0.5))

    assert session.project == _project()
    assert not session.can_undo()


def test_dropping_a_region_the_document_has_not_got_pushes_nothing(tmp_path: Path) -> None:
    session = _opened(tmp_path, Replicate(name="north"))

    with pytest.raises(KeyError):
        issue(session, RemoveReplicate("nowhere"))

    # A refused intent and a no-op are different outcomes, which is what the
    # raise buys: filtering a list by an id nothing matches would drop the
    # gesture silently and leave the caller's selection pointing at a region it
    # believes it removed.
    assert len(session.project.replicates) == 1
    assert not session.can_undo()
