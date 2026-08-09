"""Declarations checked by running them, over whatever `discover()` returns.

`tests/unit/test_cache_admission.py` is the shape: a claim a tool makes about
itself is put through the executor rather than read back out of the spec. Three
of the remaining declarations are load-bearing in the same way — `mode` is what
the executor branches on, `element` is the noun a count leaves the process
under, and `version` is a position in the cache key — and each of them survived
being mutated on `crop` with the whole unit suite green.

Generic over the shelf and not a table with a row per tool. A row would be the
shared list `adr/a-tool-is-one-file.md` exists to keep tools out of, and a table
of expected values would certify a declaration with a copy of itself, which is
`adr/declared-means-verified.md`'s last clause. So every case here derives its
expectation from what the run did and compares the *declaration* against it.

**What a run cannot settle, and is therefore not asserted below.**
`ElementRelation` is a claim about the meaning of an emitted value, and the only
thing a run exposes is how many values there are. `crop` separates the two: it
emits strictly fewer elements than it consumed and every one of them is still a
pixel, so "preserving" cannot be read off the element count in either direction
(`findings/2026.08.07-the-element-relation-is-not-decidable-from-a-run.md`). The
concrete kinds are decidable and are checked; the relation half stays open, and
a table of the shape this file refuses would not close it either — it would pass
forever on a tool whose declaration is consistently wrong in both places.

Real tools rather than fixtures, for `test_cache_admission.py`'s reason: what is
under test is a declaration shipped tools make.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import cv2
import numpy as np
import pytest

from sieve.core.pipeline_model import Node, Pipeline, SourceSpan
from sieve.core.tool_base import (
    ArraySpec,
    ElementKind,
    ElementRelation,
    Mode,
    ToolSpec,
    node_warmup_frames,
)
from sieve.core.tool_registry import ToolRegistry
from sieve.core.types import ChannelSpec, Frame
from sieve.pipeline.cache_key import NotCacheableError, is_cacheable, node_key
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import FrameResult, execute
from sieve.pipeline.plan import ExecutionPlan
from sieve.tools import discover

#: The shelf, resolved once at import. Parametrising over it is what makes a
#: tool landing tomorrow enter these cases without editing them.
SHELF = discover()

SOURCE = "footage|1|2"
NODE = "n"

#: Big enough that a tool dividing the frame into a grid emits more than one
#: cell — `block_signal`'s automatic block is 64 px at full scale, so a 64x64
#: frame would make a block-emitting tool indistinguishable from a
#: frame-emitting one. Small enough that `detect`'s window costs a second.
WIDTH = HEIGHT = 128

#: Short, because what the width cases need is that the executor reached the
#: node at all. `detect` reads 247 frames either side of every frame it answers
#: for, so each frame asked for here is a Morlet transform over five hundred.
SPAN = SourceSpan(start=0, end=2)

#: Long enough to hold a frame either side of `ALTERED`, which is what the
#: perturbation case compares across.
NEIGHBOURHOOD = SourceSpan(start=0, end=6)

#: The frame the perturbed footage differs at, and the seed offset that makes it
#: differ. Interior to `NEIGHBOURHOOD` so there are unaltered frames on both
#: sides to read the answer at.
ALTERED = 3
ALTERED_SEED = 1000

GOLDENS = Path(__file__).resolve().parents[1] / "goldens"

#: A stand-in for whatever the walk hands a root, as `test_cache_key.py` spells
#: it: in schema v1 a root's upstream is the source key and no node has no input.
UPSTREAM = "upstream-key"

#: A version no tool has, for the bump. Nothing about it is special except that
#: it is not the registered one.
BUMPED = "9.9.9"


class Footage:
    """Frames a tool's own `accepts` admits, each index a different field.

    Derived from the declaration rather than fixed, because the tools disagree
    about what they can be fed and a single dtype would leave `detect` and
    `motion_history` unrunnable. That is not the declaration certifying itself:
    `accepts` decides what goes *in*, and every assertion below is about what
    came out.

    Noise rather than a ramp, for `test_cache_admission.py`'s reason — a ramp
    differences to a constant, and a differencing tool would then emit the same
    frame whichever frames it was handed, which is exactly the substitution the
    perturbation case is looking for.
    """

    def __init__(self, spec: ToolSpec, *, altered: int | None = None) -> None:
        accepts = spec.accepts
        assert isinstance(accepts, ArraySpec)
        self.dtype = np.dtype(accepts.dtypes[0] if accepts.dtypes else "uint8")
        self.channels = accepts.channels[0] if accepts.channels else ChannelSpec.GRAY
        self.altered = altered
        self.handed: list[Frame] = []

    def read(self, index: int) -> Frame:
        seed = ALTERED_SEED if index == self.altered else index
        rng = np.random.default_rng(seed)
        shape = (HEIGHT, WIDTH) if self.channels is ChannelSpec.GRAY else (HEIGHT, WIDTH, 3)
        if self.dtype.kind in "ui":
            data = rng.integers(0, 256, shape, dtype=self.dtype)
        else:
            data = rng.random(shape).astype(self.dtype)
        frame = Frame(data=data, index=index, channels=self.channels)
        self.handed.append(frame)
        return frame


class RecordedSource:
    """A `ToolSource` that counts the frames the executor asked it for.

    The source tool's half of the recorder below. What it records is a width of
    one per call, which is what a source tool's answer to the mode question is:
    it is asked for the frame the run is answering for, one at a time, and it
    accumulates nothing.
    """

    def __init__(self, inner: object, widths: list[int]) -> None:
        self._inner = inner
        self._widths = widths

    def file(self, params: object, /) -> Path:
        return self._inner.file(params)  # pyright: ignore[reportAttributeAccessIssue]

    def read(self, params: object, index: object, /) -> Frame:
        self._widths.append(1)
        return self._inner.read(params, index)  # pyright: ignore[reportAttributeAccessIssue]


def observe(
    spec: ToolSpec, span: SourceSpan, footage: Footage, params: dict[str, object] | None = None
) -> tuple[list[int], list[FrameResult]]:
    """Run `spec` as a single-node graph, recording the window each call got.

    The recorder is swapped in with `dataclasses.replace`, which changes no
    declaration — `run` and `source` are pointers the executor follows, so
    wrapping one leaves every claim under test exactly as the tool wrote it. A
    scratch registry rather than the process-wide shelf, because the replacement
    must not outlive this call.

    A root and nothing above it: what a tool is handed here is the reader's
    frame, so the width the executor chose is the tool's own declaration and not
    an upstream's lookahead accumulated into it. A source tool is a root that is
    handed nothing at all — the footage below is built and never read — and the
    pointer it declares instead is the one wrapped.
    """
    widths: list[int] = []
    shelf = ToolRegistry()
    if spec.source is not None:
        shelf.register(dataclasses.replace(spec, source=RecordedSource(spec.source, widths)))
    else:
        assert spec.run is not None, f"{spec.tool_id} points at no run and cannot be executed"
        kernel = spec.run

        def recorded(params: object, window: object, state: object, /) -> Frame:
            widths.append(len(window))  # pyright: ignore[reportArgumentType]
            return kernel(params, window, state)  # pyright: ignore[reportArgumentType]

        shelf.register(dataclasses.replace(spec, run=recorded))
    pipeline = Pipeline(
        nodes=(
            Node(
                node_id=NODE,
                tool_id=spec.tool_id,
                version=spec.version,
                params=dict(params or {}),
            ),
        ),
        edges=(),
    )
    plan = ExecutionPlan.build(Dag.build(pipeline, shelf), source=SOURCE, span=span)
    return widths, list(execute(plan, footage))


@pytest.fixture(scope="module")
def picked(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    """Params pointing every path parameter on the shelf at one written picture.

    Derived from `ToolSpec.path_params` — the kind, never a tool id — so this is
    the same shape as everything else here: a tool that lands tomorrow with a
    file to read is handed one without this file learning its name. The picture
    is the size `Footage` hands every other tool, so a case comparing an emitted
    frame against its input is comparing like with like.
    """
    path = tmp_path_factory.mktemp("picked") / "plate.png"
    rng = np.random.default_rng(7)
    cv2.imwrite(str(path), rng.integers(0, 256, (HEIGHT, WIDTH), dtype=np.uint8))
    return {"path": path}


def params_for(spec: ToolSpec, picked: dict[str, object]) -> dict[str, object]:
    """This tool's node params: nothing, or the picture for its path parameters."""
    return {name: str(picked["path"]) for name in spec.path_params}


def node_for(spec: ToolSpec) -> Node:
    """The node every key below is derived from: this tool at its defaults."""
    return Node(node_id=NODE, tool_id=spec.tool_id, version=spec.version, params={})


def golden_for(spec: ToolSpec) -> Path:
    return GOLDENS / f"cache_key_{spec.tool_id}_{spec.version}.txt"


@pytest.mark.parametrize("spec", SHELF, ids=lambda spec: spec.tool_id)
def test_mode_is_what_the_run_does(spec: ToolSpec, picked: dict[str, object]) -> None:
    """A windowed tool is handed a span, and a streaming one the frame in front of it.

    `Mode` is what the executor branches on, so a tool declaring the wrong one
    produces a graph that validates, runs, and is wrong about what it computed.
    Both halves are read off the calls the run actually made.

    The windowed half is where the silence was. `WINDOWED` with nothing to
    window is a claim with no subject in `WarmupKind`'s sense: the executor
    hands such a node the same one frame a streaming node gets, so the
    declaration bought nothing and cost the interactive loop a decode per frame
    — a windowed node is fed its input on a warm re-render whether or not the
    store answered (`pipeline/executor.py`). Asserting the width rather than the
    declared numbers is what makes that fail rather than agree with itself.

    The streaming half is checked against the run twice over: the calls are one
    frame wide, and — for a tool that also declares no state and no warmup — the
    answer does not move when a neighbouring frame is replaced. That second leg
    is the one a spec cannot fake, and it is skipped for a tool with something to
    settle, whose answer depends on its predecessors by declaration.
    """
    settings = params_for(spec, picked)
    widths, _ = observe(spec, SPAN, Footage(spec), settings)
    assert widths, f"{spec.tool_id} was never called; there is nothing to read a mode off"

    if spec.mode is Mode.WINDOWED:
        assert min(widths) > 1, (
            f"{spec.tool_id} declares mode=windowed and was handed {min(widths)} frame(s) — a "
            "window of one is what a streaming node gets, so this declaration accumulates "
            "nothing and only costs the node its input on every warm frame"
        )
        return

    assert set(widths) == {1}, (
        f"{spec.tool_id} declares mode=streaming and was handed windows of {sorted(set(widths))}"
    )
    if spec.stateful or node_warmup_frames((spec, spec.params_model())).frames > 0:
        return

    plain = dict(_by_index(observe(spec, NEIGHBOURHOOD, Footage(spec), settings)[1]))
    perturbed = dict(
        _by_index(observe(spec, NEIGHBOURHOOD, Footage(spec, altered=ALTERED), settings)[1])
    )
    for index, frame in plain.items():
        if index == ALTERED:
            continue
        assert np.array_equal(frame.data, perturbed[index].data), (
            f"{spec.tool_id} declares no state and no warmup, so its answer at frame {index} is "
            f"the frame in front of it — but replacing frame {ALTERED} moved it"
        )


def _by_index(results: list[FrameResult]) -> list[tuple[int, Frame]]:
    return [(int(result.index), result[NODE]) for result in results]


@pytest.mark.parametrize("spec", SHELF, ids=lambda spec: spec.tool_id)
def test_element_is_what_the_run_emits(spec: ToolSpec, picked: dict[str, object]) -> None:
    """The dtype, the channels and the element kind, against the frame handed back.

    `emits` is what `dag.py` chains an edge on and `element` is the noun a count
    over that edge is denominated in, so both are wrong silently: the graph
    validates, the run completes, and the number reaches a CSV under a word
    nothing checked.

    The element half is an equivalence in one direction and an implication in
    the other, which is what the run supports. A frame-wide value is *decidable*
    — one value came back for a frame of many — so `FRAME` is asserted both
    ways, and a tool that quietly stopped reducing to a scalar fails here even
    though its declaration still parses. `BLOCK` is coarser than its input and
    finer than a scalar, which is checkable but not sufficient: an aggregating
    relation looks the same from here, and telling them apart needs the meaning
    rather than the count (see this module's docstring).
    """
    footage = Footage(spec)
    _, results = observe(spec, SPAN, footage, params_for(spec, picked))
    assert results, f"{spec.tool_id} answered for no frame"
    produced = results[0][NODE]
    assert isinstance(spec.emits, ArraySpec)

    if spec.emits.dtypes:
        assert produced.data.dtype.name in spec.emits.dtypes, (
            f"{spec.tool_id} emitted {produced.data.dtype.name} and declares {spec.emits.dtypes}"
        )
    if spec.emits.channels:
        assert produced.channels in spec.emits.channels, (
            f"{spec.tool_id} emitted {produced.channels} and declares {spec.emits.channels}"
        )

    assert (produced.data.size == 1) is (spec.element is ElementKind.FRAME), (
        f"{spec.tool_id} declares element={spec.element} and emitted {produced.data.size} "
        f"value(s) — one value for the whole frame is {ElementKind.FRAME!r} and nothing else"
    )
    if spec.source is not None:
        # The three legs below relate what came out to what went in, and a
        # source tool was handed nothing: it opened its own file, so `footage`
        # was built and never read. The two legs above are the ones that still
        # have a subject.
        assert not footage.handed, f"{spec.tool_id} declares a source and read the footage anyway"
        return
    consumed = footage.handed[0]
    assert consumed.data.size > 1, "a one-element input cannot tell the element kinds apart"
    if spec.element is ElementKind.BLOCK:
        assert produced.data.size < consumed.data.size, (
            f"{spec.tool_id} declares element={spec.element} and emitted as many values as it "
            "consumed, so nothing was divided into a grid"
        )
    if spec.element is ElementRelation.AGGREGATED:
        assert produced.data.size <= consumed.data.size, (
            f"{spec.tool_id} declares it aggregates and emitted more values than it consumed"
        )


@pytest.mark.parametrize("spec", SHELF, ids=lambda spec: spec.tool_id)
def test_a_version_bump_moves_the_key(spec: ToolSpec) -> None:
    """`version` has no behavioural referent, so it is pinned where it has a consequence.

    Nothing a run does makes `2.0.0` false — which is why the sweep over
    `crop` could set it and leave the suite green. What it *is* is a position in
    the node key (`cache_key.NODE_KEY_POSITIONS`), so a wrong value serves
    another build's results for a computation that never produced them.

    One golden per tool, in the shape `tests/goldens/` already uses: a file a
    tool adds beside itself rather than a row it has to enter in a list here,
    which is `adr/a-tool-is-one-file.md`'s whole subject. The file pins the
    tool's parameter defaults into the key as well, and that is intended — a
    changed default is a changed computation, and a golden that moved is the
    only notice the store gives.

    A tool the policy refuses has no key to pin. Asserting the refusal rather
    than skipping keeps the two sides of `cache_policy` accounted for here:
    every tool on the shelf is either pinned or named as one that recomputes.
    """
    golden = golden_for(spec)
    if not is_cacheable(spec):
        assert not golden.exists(), (
            f"{spec.tool_id} may not be keyed under cache_policy, so {golden.name} pins a key "
            "nothing can ask for"
        )
        with pytest.raises(NotCacheableError):
            node_key(node_for(spec), spec=spec, upstream=UPSTREAM)
        return

    key = node_key(node_for(spec), spec=spec, upstream=UPSTREAM)
    assert golden.exists(), (
        f"{spec.tool_id} is keyed and has no cache-key golden — write {key} into "
        f"tests/goldens/{golden.name}"
    )
    assert golden.read_text(encoding="utf-8").strip() == key, (
        f"{spec.tool_id} {spec.version} now keys to {key}, and {golden.name} holds another "
        "digest. Either the tool changed what it computes, in which case its version moves and "
        "this file is replaced, or a key position moved and HASH_VERSION is the remedy"
    )

    bumped = dataclasses.replace(spec, version=BUMPED)
    assert node_key(node_for(bumped), spec=bumped, upstream=UPSTREAM) != key, (
        f"{spec.tool_id} keys the same at {spec.version} and {BUMPED}, so two versions of one "
        "tool share cache entries and the older pipeline is served the newer tool's frames"
    )
