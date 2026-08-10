"""Every mutation of the open project, entering as one intent.

Each case here stands in for a way the layer stops being the document's only
writer, or stops being keyed by *what was mutated* rather than by what emitted
it: a value that lands somewhere the undo stack cannot reach, an override that
needs a kind of its own, a checkoff that moves a cache key, or a refused intent
that pushes a value anyway.
"""

from __future__ import annotations

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
from sieve.session.intents import AddNode, RemoveNode, SetOutputs, SetParam, issue
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


def test_an_intent_naming_no_node_leaves_the_session_where_it_was(tmp_path: Path) -> None:
    session = _opened(tmp_path)

    with pytest.raises(KeyError):
        issue(session, SetParam(node_id="nowhere", param="level", value=0.5))

    assert session.project == _project()
    assert not session.can_undo()
