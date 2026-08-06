"""What the wizard can offer at a seam, and what each offer would do to the chain.

Qt-free like `gui/chain_model.py`, and one layer over it: the chain model
grades chains, this module builds the *hypothetical* chains a seam click puts
on the table and grades those. The wizard widget is a presentation over the
`Candidate` tuple this returns; nothing here paints and nothing here renders.

**The catalog is transitional.** The remaining parity rows still carry explicit
stack facts, but newly registered single-port streaming filters are projected
from `FilterSpec.authoring_group` and element declarations. The two tab-side
suffix steps stay explicit shell operations until the v6 graph migration gives
them graph identity.

**The wizard cannot break the chain** (parity plan § 2). An entry whose input
kind does not match the seam is not listed at all; an entry that fits but
would conflict downstream is listed disabled with "breaks below"; an entry
already in the chain is listed disabled with "in chain" — learning 8's
default, blocking duplicates until a real chain needs repetition. Enabled
means exactly one thing: the hypothetical chain grades conflict-free.

**Guidance is user-facing UI content** (learning 7). The wizard pane is built
from the filter's own markdown, split into sections by `sieve.filters` — the
package that owns §3's "one module + one markdown" owns what the markdown is
made of. What is left here is the dispatch: the two tab-side steps have no
`.md`, so their guidance is inline, because their parameters are the detector
the wizard's center column already shows live.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from sieve.core.filter_base import (
    DEFAULT_PORT,
    AuthoringGroup,
    ElementKind,
    FilterSpec,
    Mode,
    TableSpec,
)
from sieve.core.filter_registry import REGISTRY, FilterRegistry, UnknownFilterError
from sieve.core.pipeline_model import Node, Pipeline
from sieve.filters import Guidance, discover
from sieve.filters import guidance_for as _filter_guidance
from sieve.gui.chain_model import (
    ChainKind,
    ChainStep,
    DetectorState,
    LiveChain,
    Stage,
    Status,
    grade,
)
from sieve.pipeline.dag import linear_order

#: Disable reasons, verbatim from the mockup's success criteria. A candidate
#: with an empty reason is enabled.
IN_CHAIN = "in chain"
BREAKS_BELOW = "breaks below"
CONFLICT_ABOVE = "conflict above — repair it first"


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """One operation the wizard can offer.

    `entry_id` doubles as the step id a commit mints — safe because
    duplicates are blocked, so no chain holds two steps from one entry.
    `filter_id` is None for the tab-side suffix steps; `hidden_params` names
    node params the settings pane must not offer because they mirror chain
    state rather than user intent (`block_signal`'s scale and fps).
    """

    entry_id: str
    title: str
    stage: Stage
    kind_in: ChainKind
    kind_out: ChainKind
    blurb: str
    filter_id: str | None = None
    hidden_params: frozenset[str] = frozenset()
    #: Learning 8's per-filter judgment. Everything defaults to blocking a
    #: second copy; a legitimately repeatable operation flips this when one
    #: exists.
    repeatable: bool = False


@dataclass(frozen=True, slots=True)
class Candidate:
    """One catalog entry judged against one seam: offered, or refused with why."""

    entry: CatalogEntry
    enabled: bool
    reason: str = ""


#: Inline guidance for the steps that have no filter module to keep an `.md`
#: beside. Written for the same reader: someone deciding in the wizard.
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


_GROUP_TO_STAGE: dict[AuthoringGroup, Stage] = {
    AuthoringGroup.SOURCE_PREP: Stage.SPATIAL_PREP,
    AuthoringGroup.SPATIAL_PREP: Stage.SPATIAL_PREP,
    AuthoringGroup.SIGNAL_EXTRACTION: Stage.EXTRACTION,
    AuthoringGroup.TEMPORAL_FILTER: Stage.TEMPORAL_FILTER,
    AuthoringGroup.DETECTION: Stage.DETECTION,
}
_STAGE_ORDER = {stage: index for index, stage in enumerate(Stage)}
_TITLE_ACRONYMS = frozenset({"ema"})


def catalog(*, registry: FilterRegistry | None = None) -> tuple[CatalogEntry, ...]:
    """Every operation the wizard can offer, in stage order.

    Node-backed entries take their blurb from the registered spec's summary —
    the same one line `sieve inspect` prints — so the row and the CLI never
    tell different stories. Calls `discover()` first for the reason
    `PreviewRunner` does: a caller should not have to know the shelf needed
    populating.
    """
    shelf = _shelf(registry)
    explicit = _legacy_catalog(shelf)
    explicit_filter_ids = frozenset(e.filter_id for e in explicit if e.filter_id is not None)
    return (*explicit, *_declared_catalog_entries(shelf, explicit_filter_ids))


def _shelf(registry: FilterRegistry | None) -> FilterRegistry:
    if registry is None:
        discover()
        return REGISTRY
    return registry


def _legacy_catalog(registry: FilterRegistry) -> tuple[CatalogEntry, ...]:
    """The parity rows not yet migrated off their explicit stack facts."""
    return (
        CatalogEntry(
            entry_id="rescale",
            title="Rescale",
            stage=Stage.SPATIAL_PREP,
            kind_in=ChainKind.IMAGE,
            kind_out=ChainKind.IMAGE,
            blurb=_summary("rescale", registry),
            filter_id="rescale",
        ),
        CatalogEntry(
            entry_id="downsample",
            title="Downsample",
            stage=Stage.SPATIAL_PREP,
            kind_in=ChainKind.IMAGE,
            kind_out=ChainKind.IMAGE,
            blurb=_summary("downsample", registry),
            filter_id="downsample",
        ),
        CatalogEntry(
            entry_id="normalize",
            title="Normalize",
            stage=Stage.SPATIAL_PREP,
            kind_in=ChainKind.IMAGE,
            kind_out=ChainKind.IMAGE,
            blurb=_summary("normalize", registry),
            filter_id="normalize",
        ),
        CatalogEntry(
            entry_id="background_ema",
            title="Background EMA",
            stage=Stage.SPATIAL_PREP,
            kind_in=ChainKind.IMAGE,
            kind_out=ChainKind.IMAGE,
            blurb=_summary("background_ema", registry),
            filter_id="background_ema",
        ),
        CatalogEntry(
            entry_id="block_signal",
            title="Block signal",
            stage=Stage.EXTRACTION,
            kind_in=ChainKind.IMAGE,
            kind_out=ChainKind.BLOCK_SERIES,
            blurb=_summary("block_signal", registry),
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


def _declared_catalog_entries(
    registry: FilterRegistry,
    excluded_filter_ids: frozenset[str],
) -> tuple[CatalogEntry, ...]:
    entries: list[CatalogEntry] = []
    for filter_id in registry.ids():
        if filter_id in excluded_filter_ids:
            continue
        spec = registry.latest(filter_id)
        entry = _entry_from_spec(spec)
        if entry is not None:
            entries.append(entry)
    return tuple(sorted(entries, key=_catalog_entry_key))


def _entry_from_spec(spec: FilterSpec) -> CatalogEntry | None:
    ports = spec.input_ports
    if tuple(ports) != (DEFAULT_PORT,):
        return None
    # The live stack can commit only the node-backed prefix the current
    # executor path can preview; the graph editor owns wider protocols.
    if spec.mode is not Mode.STREAMING:
        return None
    kind_in = _input_kind(spec)
    kind_out = _output_kind(spec, kind_in)
    return CatalogEntry(
        entry_id=spec.filter_id,
        title=_title_for(spec.filter_id),
        stage=_GROUP_TO_STAGE[spec.authoring_group],
        kind_in=kind_in,
        kind_out=kind_out,
        blurb=spec.summary,
        filter_id=spec.filter_id,
    )


def _input_kind(spec: FilterSpec) -> ChainKind:
    accepted = spec.input_ports[DEFAULT_PORT]
    if isinstance(accepted, TableSpec):
        return ChainKind.EVENTS
    if spec.authoring_group in {AuthoringGroup.TEMPORAL_FILTER, AuthoringGroup.DETECTION}:
        return ChainKind.BLOCK_SERIES
    return ChainKind.IMAGE


def _output_kind(spec: FilterSpec, kind_in: ChainKind) -> ChainKind:
    if isinstance(spec.emits, TableSpec):
        return ChainKind.EVENTS
    if spec.authoring_group is AuthoringGroup.DETECTION:
        return ChainKind.EVENTS
    if spec.element is ElementKind.BLOCK or kind_in is ChainKind.BLOCK_SERIES:
        return ChainKind.BLOCK_SERIES
    return ChainKind.IMAGE


def _title_for(filter_id: str) -> str:
    return " ".join(_title_word(index, word) for index, word in enumerate(filter_id.split("_")))


def _title_word(index: int, word: str) -> str:
    if word in _TITLE_ACRONYMS:
        return word.upper()
    return word.capitalize() if index == 0 else word


def _catalog_entry_key(entry: CatalogEntry) -> tuple[int, str, str]:
    return (_STAGE_ORDER[entry.stage], entry.title, entry.entry_id)


def _summary(filter_id: str, registry: FilterRegistry) -> str:
    try:
        return registry.latest(filter_id).summary
    except UnknownFilterError:
        return filter_id


# ---- judging entries against a seam -----------------------------------------


def incoming_kind(steps: tuple[ChainStep, ...], position: int) -> ChainKind | None:
    """What flows into `position`, or None when a conflict above makes it unknowable.

    The same walk `grade` does, stopped early: past the first mismatch the
    true kind is whatever the repair produces, and judging candidates against
    a guess would offer repairs that break the moment the real one lands.
    """
    current = ChainKind.IMAGE
    for step in steps[:position]:
        if step.kind_in is not current:
            return None
        current = step.kind_out
    return current


def candidates_for_insert(
    chain: LiveChain,
    seam: int,
    *,
    registry: FilterRegistry | None = None,
) -> tuple[Candidate, ...]:
    """Every offer for inserting at `seam`, suggested stage first.

    Listed: entries whose input kind matches what the seam carries. Enabled:
    those whose insertion leaves the whole chain conflict-free. When the seam
    sits below a conflict its kind is unknowable, so everything is listed and
    everything is disabled with the pointer at the real problem.
    """
    kind = incoming_kind(chain.steps, seam)
    suggested = _seam_stage(chain.steps, seam)
    offers: list[Candidate] = []
    for entry in _stage_ordered(suggested, registry):
        if kind is None:
            offers.append(Candidate(entry, enabled=False, reason=CONFLICT_ABOVE))
            continue
        if entry.kind_in is not kind:
            continue
        offers.append(
            _judge(
                entry,
                chain,
                insert_step(chain, seam, entry, registry=registry)[0].steps,
            )
        )
    return tuple(offers)


def candidates_for_swap(
    chain: LiveChain,
    step_id: str,
    *,
    registry: FilterRegistry | None = None,
) -> tuple[Candidate, ...]:
    """Every offer for replacing `step_id`, its own stage first.

    The replaced step is exempt from the duplicate rule — offering the
    current operation back is what makes the wizard double as its settings
    surface — and the incoming kind is read at the step's own position, which
    is known even when the step itself is the conflict.
    """
    position = _position(chain.steps, step_id)
    current = chain.steps[position]
    kind = incoming_kind(chain.steps, position)
    offers: list[Candidate] = []
    for entry in _stage_ordered(current.stage, registry):
        if kind is None:
            offers.append(Candidate(entry, enabled=False, reason=CONFLICT_ABOVE))
            continue
        if entry.kind_in is not kind:
            continue
        offers.append(
            _judge(
                entry,
                chain,
                swap_step(chain, step_id, entry, registry=registry)[0].steps,
                exempt=step_id,
            )
        )
    return tuple(offers)


def _judge(
    entry: CatalogEntry,
    chain: LiveChain,
    hypothetical: tuple[ChainStep, ...],
    exempt: str | None = None,
) -> Candidate:
    """One entry's verdict: the duplicate rule, then the hypothetical grade."""
    if not entry.repeatable:
        for step in chain.steps:
            if step.step_id == entry.entry_id and step.step_id != exempt:
                return Candidate(entry, enabled=False, reason=IN_CHAIN)
    if any(g.status is not Status.OK for g in grade(hypothetical)):
        return Candidate(entry, enabled=False, reason=BREAKS_BELOW)
    return Candidate(entry, enabled=True)


def _stage_ordered(
    suggested: Stage,
    registry: FilterRegistry | None = None,
) -> tuple[CatalogEntry, ...]:
    """The catalog grouped by stage with `suggested`'s group first."""
    entries = catalog(registry=registry)
    lead = tuple(e for e in entries if e.stage is suggested)
    rest = tuple(e for e in entries if e.stage is not suggested)
    return lead + rest


def _seam_stage(steps: tuple[ChainStep, ...], seam: int) -> Stage:
    """The stage a seam suggests: the step after it, else before, else the top."""
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


# ---- building the provisional chain ------------------------------------------


def build_step(
    entry: CatalogEntry,
    chain: LiveChain,
    params: dict[str, object] | None = None,
    *,
    registry: FilterRegistry | None = None,
) -> ChainStep:
    """One fresh step from `entry`, its node minted with defaults plus `params`.

    Defaults come from the registered params model — the one place a filter's
    defaults are defined — and the chain injects what mirrors its own state:
    `block_signal` reads the chain's fps and the rescale step's scale, exactly
    as `parity_chain` wires them.
    """
    node = None
    if entry.filter_id is not None:
        spec = _shelf(registry).latest(entry.filter_id)
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
    *,
    registry: FilterRegistry | None = None,
) -> tuple[LiveChain, str]:
    """The chain with `entry` inserted at `seam`, and the minted step id."""
    step = build_step(entry, chain, params, registry=registry)
    steps = (*chain.steps[:seam], step, *chain.steps[seam:])
    return replace(chain, steps=steps), step.step_id


def swap_step(
    chain: LiveChain,
    step_id: str,
    entry: CatalogEntry,
    params: dict[str, object] | None = None,
    *,
    registry: FilterRegistry | None = None,
) -> tuple[LiveChain, str]:
    """The chain with `step_id` replaced by `entry`, and the minted step id.

    Swapping a step for its own entry keeps the outgoing node's params (the
    settings surface case: the user came to reconfigure, not to reset), while
    an explicit `params` still wins — that is the wizard's own edits landing.
    """
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
    step = build_step(entry, chain, carried or None, registry=registry)
    steps = (*chain.steps[:position], step, *chain.steps[position + 1 :])
    return replace(chain, steps=steps), step.step_id


def chain_from_pipeline(
    pipeline: Pipeline,
    fps: float,
    *,
    registry: FilterRegistry | None = None,
) -> LiveChain:
    """The `LiveChain` a saved graph renders as: its nodes, plus the tab-side suffix.

    `runnable_prefix`'s inverse, for the load path — a project carries the
    node-backed prefix and the tab has to grow its stack back around it. Node
    *identity* is kept, not reminted: the loaded ids are what replicate
    overrides pin against and what cache entries are keyed on, and a chain
    that reminted them would orphan both.

    The suffix is appended from the catalog because the artifact cannot carry
    it — the temporal filter and detection steps are not nodes — and a chain
    without them would open with its graphs unreachable.

    Raises:
        GraphError: if the graph is not the one path a stack can host.
        ValueError: if it names a filter the catalog has no entry for. Refused
            rather than approximated: a stack silently missing a loaded step
            would look better-founded than it is.
    """
    entries = catalog(registry=registry)
    by_filter = {e.filter_id: e for e in entries if e.filter_id is not None}
    steps: list[ChainStep] = []
    for node in linear_order(pipeline):
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
    for entry in entries:
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
    # The default detector, not a resolved one: the caller holds the document
    # and resolves the selected replicate's values in immediately after —
    # this function knows graphs, not selections.
    return LiveChain(steps=tuple(steps), detector=DetectorState.default(fps), fps=fps)


# ---- guidance -----------------------------------------------------------------


def guidance_for(entry: CatalogEntry, *, registry: FilterRegistry | None = None) -> Guidance:
    """The pane's sections for `entry`: its filter's `.md`, or the inline text."""
    if entry.filter_id is None:
        return _TAB_SIDE_GUIDANCE[entry.entry_id]
    return _filter_guidance(_shelf(registry).latest(entry.filter_id))
