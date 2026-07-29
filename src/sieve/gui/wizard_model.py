from __future__ import annotations

from dataclasses import dataclass, replace

from sieve.core.filter_registry import REGISTRY, UnknownFilterError
from sieve.core.pipeline_model import Node, Pipeline
from sieve.filters import discover, guidance_path
from sieve.gui.chain_model import (
    ChainKind,
    ChainStep,
    DetectorState,
    LiveChain,
    Stage,
    Status,
    grade,
)


IN_CHAIN = "in chain"
BREAKS_BELOW = "breaks below"
CONFLICT_ABOVE = "conflict above — repair it first"


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    entry_id: str
    title: str
    stage: Stage
    kind_in: ChainKind
    kind_out: ChainKind
    blurb: str
    filter_id: str | None = None
    hidden_params: frozenset[str] = frozenset()

    repeatable: bool = False


@dataclass(frozen=True, slots=True)
class Candidate:
    entry: CatalogEntry
    enabled: bool
    reason: str = ""


@dataclass(frozen=True, slots=True)
class Guidance:
    summary: str
    when_to_use: str
    not_do: str
    cost: str


_TAB_SIDE_GUIDANCE: dict[str, Guidance] = {
    "morlet_band": Guidance(
        summary="Morlet wavelet band power over every block's signal.",
        when_to_use=(
            "Always, for now — it is the temporal filter, and detection counts "
            "band power. Drag the scalogram handles to choose the frequency "
            "band; the title shows the snapped band the transform actually uses."
        ),
        not_do=(
            "It does not detect anything by itself — it shapes the signal the "
            "windowed count detects on. Removing it takes every graph below "
            "with it."
        ),
        cost="The band re-sum is cheap; a frequency-band change recomputes it on release.",
    ),
    "windowed_count": Guidance(
        summary="Blocks in the value band, mean-windowed over D frames, gated.",
        when_to_use=(
            "Always, for now — it is the detection step. Place the count "
            "threshold on the green graph to arm it; until then nothing is "
            "claimed as an event."
        ),
        not_do=(
            "It does not re-run extraction. Threshold, D, and centered changes "
            "are instant pure recomputes over the retained band power."
        ),
        cost="Free — a prefix-sum mean and a comparison.",
    ),
}


def catalog() -> tuple[CatalogEntry, ...]:
    discover()
    return (
        CatalogEntry(
            entry_id="rescale",
            title="Rescale",
            stage=Stage.SPATIAL_PREP,
            kind_in=ChainKind.IMAGE,
            kind_out=ChainKind.IMAGE,
            blurb=_summary("rescale"),
            filter_id="rescale",
        ),
        CatalogEntry(
            entry_id="downsample",
            title="Downsample",
            stage=Stage.SPATIAL_PREP,
            kind_in=ChainKind.IMAGE,
            kind_out=ChainKind.IMAGE,
            blurb=_summary("downsample"),
            filter_id="downsample",
        ),
        CatalogEntry(
            entry_id="normalize",
            title="Normalize",
            stage=Stage.SPATIAL_PREP,
            kind_in=ChainKind.IMAGE,
            kind_out=ChainKind.IMAGE,
            blurb=_summary("normalize"),
            filter_id="normalize",
        ),
        CatalogEntry(
            entry_id="background_ema",
            title="Background EMA",
            stage=Stage.SPATIAL_PREP,
            kind_in=ChainKind.IMAGE,
            kind_out=ChainKind.IMAGE,
            blurb=_summary("background_ema"),
            filter_id="background_ema",
        ),
        CatalogEntry(
            entry_id="block_signal",
            title="Block signal",
            stage=Stage.EXTRACTION,
            kind_in=ChainKind.IMAGE,
            kind_out=ChainKind.BLOCK_SERIES,
            blurb=_summary("block_signal"),
            filter_id="block_signal",
            hidden_params=frozenset({"scale", "fps"}),
        ),
        CatalogEntry(
            entry_id="morlet_band",
            title="Morlet band",
            stage=Stage.TEMPORAL_FILTER,
            kind_in=ChainKind.BLOCK_SERIES,
            kind_out=ChainKind.BLOCK_SERIES,
            blurb=_TAB_SIDE_GUIDANCE["morlet_band"].summary,
        ),
        CatalogEntry(
            entry_id="windowed_count",
            title="Windowed count",
            stage=Stage.DETECTION,
            kind_in=ChainKind.BLOCK_SERIES,
            kind_out=ChainKind.EVENTS,
            blurb=_TAB_SIDE_GUIDANCE["windowed_count"].summary,
        ),
    )


def _summary(filter_id: str) -> str:
    try:
        return REGISTRY.latest(filter_id).summary
    except UnknownFilterError:
        return filter_id


def incoming_kind(steps: tuple[ChainStep, ...], position: int) -> ChainKind | None:
    current = ChainKind.IMAGE
    for step in steps[:position]:
        if step.kind_in is not current:
            return None
        current = step.kind_out
    return current


def candidates_for_insert(chain: LiveChain, seam: int) -> tuple[Candidate, ...]:
    kind = incoming_kind(chain.steps, seam)
    suggested = _seam_stage(chain.steps, seam)
    offers: list[Candidate] = []
    for entry in _stage_ordered(suggested):
        if kind is None:
            offers.append(Candidate(entry, enabled=False, reason=CONFLICT_ABOVE))
            continue
        if entry.kind_in is not kind:
            continue
        offers.append(_judge(entry, chain, insert_step(chain, seam, entry)[0].steps))
    return tuple(offers)


def candidates_for_swap(chain: LiveChain, step_id: str) -> tuple[Candidate, ...]:
    position = _position(chain.steps, step_id)
    current = chain.steps[position]
    kind = incoming_kind(chain.steps, position)
    offers: list[Candidate] = []
    for entry in _stage_ordered(current.stage):
        if kind is None:
            offers.append(Candidate(entry, enabled=False, reason=CONFLICT_ABOVE))
            continue
        if entry.kind_in is not kind:
            continue
        offers.append(
            _judge(
                entry, chain, swap_step(chain, step_id, entry)[0].steps, exempt=step_id
            )
        )
    return tuple(offers)


def _judge(
    entry: CatalogEntry,
    chain: LiveChain,
    hypothetical: tuple[ChainStep, ...],
    exempt: str | None = None,
) -> Candidate:
    if not entry.repeatable:
        for step in chain.steps:
            if step.step_id == entry.entry_id and step.step_id != exempt:
                return Candidate(entry, enabled=False, reason=IN_CHAIN)
    if any(g.status is not Status.OK for g in grade(hypothetical)):
        return Candidate(entry, enabled=False, reason=BREAKS_BELOW)
    return Candidate(entry, enabled=True)


def _stage_ordered(suggested: Stage) -> tuple[CatalogEntry, ...]:
    entries = catalog()
    lead = tuple(e for e in entries if e.stage is suggested)
    rest = tuple(e for e in entries if e.stage is not suggested)
    return lead + rest


def _seam_stage(steps: tuple[ChainStep, ...], seam: int) -> Stage:
    if seam < len(steps):
        return steps[seam].stage
    if steps:
        return steps[-1].stage
    return Stage.SPATIAL_PREP


def _position(steps: tuple[ChainStep, ...], step_id: str) -> int:
    for index, step in enumerate(steps):
        if step.step_id == step_id:
            return index
    raise KeyError(step_id)


def build_step(
    entry: CatalogEntry,
    chain: LiveChain,
    params: dict[str, object] | None = None,
) -> ChainStep:
    node = None
    if entry.filter_id is not None:
        spec = REGISTRY.latest(entry.filter_id)
        values: dict[str, object] = spec.params_model().model_dump(mode="json")
        if entry.filter_id == "block_signal":
            values["fps"] = chain.fps
            values["scale"] = _chain_scale(chain)
        values.update(params or {})
        node = Node(filter_id=entry.filter_id, version=spec.version, params=values)
    return ChainStep(
        step_id=entry.entry_id,
        title=entry.title,
        stage=entry.stage,
        kind_in=entry.kind_in,
        kind_out=entry.kind_out,
        node=node,
    )


def _chain_scale(chain: LiveChain) -> float:
    for step in chain.steps:
        if step.node is not None and step.node.filter_id == "rescale":
            return float(step.node.params.get("scale", 1.0))
    return 1.0


def insert_step(
    chain: LiveChain,
    seam: int,
    entry: CatalogEntry,
    params: dict[str, object] | None = None,
) -> tuple[LiveChain, str]:
    step = build_step(entry, chain, params)
    steps = (*chain.steps[:seam], step, *chain.steps[seam:])
    return replace(chain, steps=steps), step.step_id


def swap_step(
    chain: LiveChain,
    step_id: str,
    entry: CatalogEntry,
    params: dict[str, object] | None = None,
) -> tuple[LiveChain, str]:
    position = _position(chain.steps, step_id)
    outgoing = chain.steps[position]
    carried: dict[str, object] = {}
    if (
        outgoing.node is not None
        and entry.filter_id is not None
        and outgoing.node.filter_id == entry.filter_id
    ):
        carried = dict(outgoing.node.params)
    carried.update(params or {})
    step = build_step(entry, chain, carried or None)
    steps = (*chain.steps[:position], step, *chain.steps[position + 1 :])
    return replace(chain, steps=steps), step.step_id


def chain_from_pipeline(pipeline: Pipeline, fps: float) -> LiveChain:
    by_filter = {e.filter_id: e for e in catalog() if e.filter_id is not None}
    steps: list[ChainStep] = []
    for node in _linear_order(pipeline):
        entry = by_filter.get(node.filter_id)
        if entry is None:
            raise ValueError(f"no catalog entry for filter {node.filter_id!r}")
        steps.append(
            ChainStep(
                step_id=entry.entry_id,
                title=entry.title,
                stage=entry.stage,
                kind_in=entry.kind_in,
                kind_out=entry.kind_out,
                node=node,
            )
        )
    for entry in catalog():
        if entry.filter_id is None:
            steps.append(
                ChainStep(
                    step_id=entry.entry_id,
                    title=entry.title,
                    stage=entry.stage,
                    kind_in=entry.kind_in,
                    kind_out=entry.kind_out,
                )
            )
    return LiveChain(steps=tuple(steps), detector=DetectorState.default(fps), fps=fps)


def _linear_order(pipeline: Pipeline) -> tuple[Node, ...]:
    if not pipeline.nodes:
        return ()
    downstream_of = {edge.upstream: edge.downstream for edge in pipeline.edges}
    if len(downstream_of) != len(pipeline.edges):
        raise ValueError("graph branches — not a chain the stack can host")
    fed = {edge.downstream for edge in pipeline.edges}
    roots = [node for node in pipeline.nodes if node.node_id not in fed]
    if len(roots) != 1:
        raise ValueError(f"expected one root, found {len(roots)}")
    ordered: list[Node] = [roots[0]]
    while ordered[-1].node_id in downstream_of:
        ordered.append(pipeline.node(downstream_of[ordered[-1].node_id]))
    if len(ordered) != len(pipeline.nodes):
        raise ValueError("graph is disconnected — not a chain the stack can host")
    return tuple(ordered)


def parse_guidance(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    header = ""
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            sections[header] = "\n".join(lines).strip()
            header = line[3:].strip()
            lines = []
        else:
            lines.append(line)
    sections[header] = "\n".join(lines).strip()
    return sections


def guidance_for(entry: CatalogEntry) -> Guidance:
    if entry.filter_id is None:
        return _TAB_SIDE_GUIDANCE[entry.entry_id]
    spec = REGISTRY.latest(entry.filter_id)
    try:
        path = guidance_path(spec)
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
    except (OSError, ValueError):
        text = ""
    sections = parse_guidance(text)
    return Guidance(
        summary=spec.summary,
        when_to_use=sections.get("When to use it", ""),
        not_do=sections.get("What it does not do", ""),
        cost=sections.get("Cost", ""),
    )
