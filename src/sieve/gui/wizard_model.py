"""What the wizard can offer at a seam, and what each offer would do to the chain.

Qt-free like `gui/chain_model.py`, and one layer over it: the chain model
grades chains, this module builds the *hypothetical* chains a seam click puts
on the table and grades those. The wizard widget is a presentation over the
`Candidate` tuple this returns; nothing here paints and nothing here renders.

**The catalog is a chain-model concept, not registry metadata.** The registry
knows every filter's spec, but a spec cannot say what travels between steps —
`ArraySpec` cannot tell an image from a block grid (see
`docs/findings/2026.07.25-the-filter-contract-cannot-type-vision.md`) — and it
knows nothing of the two tab-side steps at all. So each catalog entry carries
its own kinds and stage, exactly as `parity_chain`'s steps do, and the two
suffix steps sit in the same list as the five node-backed operations because
a chain that lost one needs a way to get it back.

**The wizard cannot break the chain** (parity plan § 2). An entry whose input
kind does not match the seam is not listed at all; an entry that fits but
would conflict downstream is listed disabled with "breaks below"; an entry
already in the chain is listed disabled with "in chain" — learning 8's
default, blocking duplicates until a real chain needs repetition. Enabled
means exactly one thing: the hypothetical chain grades conflict-free.

**Guidance is user-facing UI content** (learning 7). The wizard pane is built
from the filter's own markdown — `summary` becomes the row blurb, "When to
use it" and "What it does not do" become the pane — so the `.md` beside each
filter module is read here, through the same `guidance_path` the CLI's
`sieve inspect` uses. The tab-side steps have no `.md`; their guidance is
inline, because their parameters are the detector the wizard's center column
already shows live.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from sieve.core.filter_registry import REGISTRY, UnknownFilterError
from sieve.core.pipeline_model import Node
from sieve.filters import discover, guidance_path
from sieve.gui.chain_model import ChainKind, ChainStep, LiveChain, Stage, Status, grade

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


@dataclass(frozen=True, slots=True)
class Guidance:
    """The sections the wizard pane renders, already split out of the markdown."""

    summary: str
    when_to_use: str
    not_do: str
    cost: str


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


def catalog() -> tuple[CatalogEntry, ...]:
    """Every operation the wizard can offer, in stage order.

    Node-backed entries take their blurb from the registered spec's summary —
    the same one line `sieve inspect` prints — so the row and the CLI never
    tell different stories. Calls `discover()` first for the reason
    `PreviewRunner` does: a caller should not have to know the shelf needed
    populating.
    """
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


def candidates_for_insert(chain: LiveChain, seam: int) -> tuple[Candidate, ...]:
    """Every offer for inserting at `seam`, suggested stage first.

    Listed: entries whose input kind matches what the seam carries. Enabled:
    those whose insertion leaves the whole chain conflict-free. When the seam
    sits below a conflict its kind is unknowable, so everything is listed and
    everything is disabled with the pointer at the real problem.
    """
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
    for entry in _stage_ordered(current.stage):
        if kind is None:
            offers.append(Candidate(entry, enabled=False, reason=CONFLICT_ABOVE))
            continue
        if entry.kind_in is not kind:
            continue
        offers.append(
            _judge(entry, chain, swap_step(chain, step_id, entry)[0].steps, exempt=step_id)
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


def _stage_ordered(suggested: Stage) -> tuple[CatalogEntry, ...]:
    """The catalog grouped by stage with `suggested`'s group first."""
    entries = catalog()
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
) -> ChainStep:
    """One fresh step from `entry`, its node minted with defaults plus `params`.

    Defaults come from the registered params model — the one place a filter's
    defaults are defined — and the chain injects what mirrors its own state:
    `block_signal` reads the chain's fps and the rescale step's scale, exactly
    as `parity_chain` wires them.
    """
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
    """The chain with `entry` inserted at `seam`, and the minted step id."""
    step = build_step(entry, chain, params)
    steps = (*chain.steps[:seam], step, *chain.steps[seam:])
    return replace(chain, steps=steps), step.step_id


def swap_step(
    chain: LiveChain,
    step_id: str,
    entry: CatalogEntry,
    params: dict[str, object] | None = None,
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
    step = build_step(entry, chain, carried or None)
    steps = (*chain.steps[:position], step, *chain.steps[position + 1 :])
    return replace(chain, steps=steps), step.step_id


# ---- guidance -----------------------------------------------------------------


def parse_guidance(text: str) -> dict[str, str]:
    """`## ` sections of a guidance file, header → body, reading order.

    The intro before the first `##` lands under `""`. Deliberately dumb — the
    guidance files are house-written markdown, and a parser that understood
    more of it would invite prose that renders here and nowhere else.
    """
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
    """The pane's sections for `entry`: its `.md` split up, or the inline text.

    A node-backed filter whose guidance file is missing degrades to its
    summary — the same posture as `sieve inspect`, which prints the absence
    rather than failing, because an out-of-tree filter is allowed to exist
    before its documentation does.
    """
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
