"""The live tab's chain and detector, as Qt-free state the stack renders.

The chain is a hybrid (parity plan § 2): the spatial-prep and extraction
steps are real pipeline nodes — `runnable_prefix` turns them into the
`Pipeline` value the tab hands `PreviewRunner` — while the temporal filter
and detection are tab-side derivation over the collected series
(`recompute`). The stack widgets are one presentation over this model; the
wizard's provisional chain is another instance of the same types.

**Kinds are a chain-model concept, not `FilterSpec` metadata.** `ArraySpec`
cannot distinguish an image frame from a `(ny, nx)` block-series frame —
both are GRAY float32 arrays (see
`docs/findings/2026.07.25-the-filter-contract-cannot-type-vision.md`) — so
each step carries its own `kind_in`/`kind_out` and `grade` walks them. The
type-system version of this question comes due when the temporal filter
becomes a real windowed node (plan § 7), not before.

**`grade` never throws** (plan learning 1). `Dag.build` raises on the first
bad edge, which is right for execution and useless for a stack that must
draw a chain a removal or a loaded file broke: every step gets ok /
conflict / unreached, the conflict names what it expects and what it is
receiving, and everything after the first conflict is unreached rather than
a cascade of conflicts.

**Unset count threshold = disarmed.** `DetectorState.count_frac` is `None`
until the user places the handle, `recompute` produces no gate and no
intervals for it, and the footer says so. v1's unset-means-unbounded painted
a fresh tab as one giant detection; a band the user never placed claims
nothing here. Frequency and value bands default wide open instead — they
shape a signal, they don't claim an event.

**Reset is parameters-not-structure.** `reset()` returns the same steps with
default parameters and a default detector; the chain the user built stays.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import NDArray

from sieve.core.detection import (
    count_band_to_counts,
    detect_gate,
    gate_intervals,
    inband_count,
    windowed_mean,
)
from sieve.core.pipeline_model import DetectorSettings, Edge, Node, Pipeline
from sieve.core.wavelet import band_indices, default_freqs, morlet_band_power
from sieve.filters.block_signal import resolve_block

FloatArray = NDArray[np.floating[Any]]

#: How the extraction signals read on their card and quick-switch.
SIGNAL_LABELS: dict[str, str] = {
    "change_energy": "change energy (Jtt)",
    "flow_speed": "LK optical flow",
    "coherence": "coherence (0-1)",
}


class ChainKind(StrEnum):
    """What travels between two steps, at the granularity the stack grades.

    Deliberately not `core.filter_base.StreamKind`: that one cannot tell an
    image from a block grid (see the module docstring), and this one exists
    for exactly that distinction.
    """

    IMAGE = "image"
    BLOCK_SERIES = "block series"
    EVENTS = "events"


class Stage(StrEnum):
    """The fixed headers the stack groups cards under, in chain order."""

    SPATIAL_PREP = "spatial prep"
    EXTRACTION = "signal extraction"
    TEMPORAL_FILTER = "temporal filter"
    DETECTION = "detection"


class Status(StrEnum):
    """One step's grade."""

    OK = "ok"
    CONFLICT = "conflict"
    UNREACHED = "unreached"


@dataclass(frozen=True, slots=True)
class ChainStep:
    """One card of the stack.

    `node` is set for the pipeline-backed prefix (rescale, normalize,
    block_signal) and `None` for the tab-side suffix (morlet band, windowed
    count). The distinction is what `runnable_prefix` walks; the kinds are
    what `grade` walks; the stage is what the headers group by.
    """

    step_id: str
    title: str
    stage: Stage
    kind_in: ChainKind
    kind_out: ChainKind
    node: Node | None = None


@dataclass(frozen=True, slots=True)
class StepGrade:
    """One step's status, with the conflict spelled out for its card."""

    status: Status
    #: For a conflict: "expects image, receiving block series". Empty
    #: otherwise — the message *is* the repair prompt, so it exists only when
    #: there is something to repair.
    message: str = ""


def grade(steps: tuple[ChainStep, ...]) -> tuple[StepGrade, ...]:
    """Every step's status, for a chain in any state at all.

    The walk carries one kind — the source is an image — and compares each
    step's `kind_in` against it. The *first* mismatch is the conflict; every
    step after it is unreached, because its true input is unknowable until
    the conflict is repaired and grading it against a guess would paint
    repairable chains as wrecks.
    """
    grades: list[StepGrade] = []
    current = ChainKind.IMAGE
    broken = False
    for step in steps:
        if broken:
            grades.append(StepGrade(Status.UNREACHED))
        elif step.kind_in is not current:
            grades.append(
                StepGrade(
                    Status.CONFLICT,
                    f"expects {step.kind_in}, receiving {current}",
                )
            )
            broken = True
        else:
            grades.append(StepGrade(Status.OK))
            current = step.kind_out
    return tuple(grades)


def runnable_prefix(steps: tuple[ChainStep, ...]) -> Pipeline:
    """The `Pipeline` value of the ok node-backed prefix, edges included.

    Stops at the first step that is not ok or not node-backed: a conflicted
    chain still previews the video through whatever prefix survives, which is
    what "no reachable step, no graph" means for the *graphs* while the
    footage stays watchable.
    """
    nodes: list[Node] = []
    for step, step_grade in zip(steps, grade(steps), strict=True):
        if step_grade.status is not Status.OK or step.node is None:
            break
        nodes.append(step.node)
    edges = tuple(
        Edge(upstream=a.node_id, downstream=b.node_id) for a, b in itertools.pairwise(nodes)
    )
    return Pipeline(nodes=tuple(nodes), edges=edges)


@dataclass(frozen=True, slots=True)
class DetectorState:
    """The tab-side suffix's parameters: bands, window, arming, solo.

    Frozen, so every edit is a `replace(...)` and the two-tier drag
    discipline has a value to hand each tier. Bands are in the units the
    plots drag them in; the count threshold alone is a *fraction* of the
    region's blocks (`core.detection.count_band_to_counts` is the one
    denomination point).
    """

    #: Frequency band in Hz over the Morlet bank. Wide open by default;
    #: handles clamp to the bank's edges, so `inf` here means "the top row".
    freq_band: tuple[float, float] = (0.0, math.inf)
    #: Value band over band power. Wide open by default.
    value_band: tuple[float, float] = (-math.inf, math.inf)
    #: Count threshold as fractions of region blocks, or None = disarmed:
    #: nothing is green and the footer says so until the user places it.
    count_frac: tuple[float, float] | None = None
    #: Detection window D, in frames. The label shows frames and seconds.
    window_frames: int = 30
    centered: bool = True
    #: A block soloed from the heat panel, as its column in the series, or
    #: None for the whole population.
    solo_block: int | None = None

    @property
    def armed(self) -> bool:
        """Whether a count threshold exists to detect with."""
        return self.count_frac is not None

    @classmethod
    def default(cls, fps: float) -> DetectorState:
        """The documented defaults: wide-open bands, disarmed, D of one second."""
        return cls(window_frames=max(1, round(fps)))

    def as_settings_changes(self) -> dict[str, Any]:
        """This state as `DetectorSettings` fields — what a document edit submits.

        `solo_block` is deliberately absent: soloing is looking, not tuning,
        and the artifact refuses to carry it (`core.pipeline_model`'s module
        docstring). Prefer submitting a *subset* of this — only the fields
        the gesture touched — for `edited_params`' baseline-drag reason.
        """
        return {
            "freq_band": self.freq_band,
            "value_band": self.value_band,
            "count_frac": self.count_frac,
            "window_frames": self.window_frames,
            "centered": self.centered,
        }

    @classmethod
    def from_settings(cls, settings: DetectorSettings, *, solo_block: int | None) -> DetectorState:
        """The live state a resolved artifact value renders as.

        `solo_block` is threaded through from the state being replaced,
        because the artifact does not carry it and a replicate switch must
        not silently un-solo the block the user is inspecting.
        """
        return cls(
            freq_band=settings.freq_band,
            value_band=settings.value_band,
            count_frac=settings.count_frac,
            window_frames=settings.window_frames,
            centered=settings.centered,
            solo_block=solo_block,
        )


@dataclass(frozen=True, slots=True)
class DetectorUpdate:
    """One pure recompute over one collected series.

    `band_power` is retained so value-band / threshold / D re-tunes are the
    cheap tier (no transform); a frequency-band or upstream change discards
    it and recomputes. `gate` and `intervals` are None when disarmed — not
    empty, which would be "armed and found nothing".
    """

    band_power: NDArray[np.float32]  # (T, B)
    count: NDArray[np.float32]  # (T,)
    windowed: NDArray[np.float32]  # (T,)
    gate: NDArray[np.bool_] | None
    intervals: tuple[tuple[int, int], ...] | None
    #: The snapped bank rows the transform actually used — what the
    #: scalogram title renders (the title tells the truth the transform uses).
    band_rows: tuple[int, int]


def recompute(
    series: FloatArray,
    fps: float,
    state: DetectorState,
    *,
    start_index: int = 0,
    band_power: NDArray[np.float32] | None = None,
    workers: int,
) -> DetectorUpdate:
    """Item 1's functions glued into the one derivation the tab repeats.

    `series` is the collected `(T, B)` block-signal columns. Pass the
    previous update's `band_power` when only the value band, threshold, D,
    or centered changed — the cheap tier — and leave it None when the
    frequency band or anything upstream moved.

    `start_index` is the series' first source frame, so intervals come back
    in absolute frames (what the seeker's ticks jump to).

    `workers` caps the transform's threads and is **required, with no default**.
    It had one — `ALL_CORES` — and `gui/filter_tab.py` inherited it by omission,
    running a full Morlet transform over every core on the GUI thread beside two
    decode pools. That is the fourth consumer `gui/concurrency.py` exists to
    forbid, and `tests/unit/test_concurrency.py` could not see it: a test that
    sums declared constants checks the declaration, not the calls. Deleting the
    default moves enforcement to pyright, which checks every call site.

    A headless caller wanting the whole machine passes `ALL_CORES` and says so.
    Anything running beside the interactive pools passes
    `concurrency.DETECTOR_WORKERS`.
    """
    freqs = default_freqs(fps)
    i, j = band_indices(freqs, state.freq_band[0], state.freq_band[1])
    if band_power is None:
        band_power = morlet_band_power(series, fps, freqs, i, j, workers=workers)
    count = inband_count(band_power, state.value_band[0], state.value_band[1])
    windowed = windowed_mean(count, state.window_frames, state.centered)
    if state.count_frac is None:
        gate = None
        intervals = None
    else:
        lo, hi = count_band_to_counts(state.count_frac[0], state.count_frac[1], band_power.shape[1])
        gate = detect_gate(windowed, lo, hi)
        intervals = tuple(gate_intervals(gate, start=start_index))
    return DetectorUpdate(
        band_power=band_power,
        count=count,
        windowed=windowed,
        gate=gate,
        intervals=intervals,
        band_rows=(i, j),
    )


def snapped_band_label(freq_band: tuple[float, float], fps: float) -> str:
    """The *snapped* frequency band, as the scalogram title and caption render it.

    Snapped, not the handle positions: `band_indices` is what the transform
    actually uses, and the title tells the truth the transform uses (plot
    contracts, parity plan § 2). `[i, j)` is half-open, so the upper edge is
    row `j - 1`.
    """
    freqs = default_freqs(fps)
    i, j = band_indices(freqs, freq_band[0], freq_band[1])
    return f"band {freqs[i]:.2f}-{freqs[j - 1]:.2f} Hz"


def caption_for(step: ChainStep, detector: DetectorState, fps: float) -> str:
    """One line restating the step's current values.

    Captions are what makes a collapsed reading of the stack complete (plan
    § 2): every parameter a card's widgets hold is restated here in words, so
    scanning titles and captions answers "what is this chain doing" without
    opening anything. Node-backed steps read their captions from the node's
    params — the same values the pipeline runs — and the tab-side suffix
    reads from the detector, so a caption can never disagree with the value
    it restates.
    """
    node = step.node
    if node is not None:
        if node.filter_id == "rescale":
            return f"scale {float(node.params['scale']):.2f} · area"
        if node.filter_id == "normalize":
            return str(node.params["mode"])
        if node.filter_id == "block_signal":
            signal = str(node.params["signal"])
            label = SIGNAL_LABELS.get(signal, signal)
            block = int(node.params["block"])
            scale = float(node.params["scale"])
            shown = f"auto ({resolve_block(0, scale)})" if block == 0 else str(block)
            return f"{label} · block {shown}"
        return node.filter_id
    if step.stage is Stage.TEMPORAL_FILTER:
        return snapped_band_label(detector.freq_band, fps)
    if step.stage is Stage.DETECTION:
        d = detector.window_frames
        seconds = d / fps if fps > 0 else 0.0
        return f"D {d} fr ({seconds:.2f} s) · {_threshold_caption(detector)}"
    return step.title


def _threshold_caption(detector: DetectorState) -> str:
    """The count threshold in words, fraction-denominated like the state."""
    if detector.count_frac is None:
        return "threshold off"
    lo, hi = detector.count_frac
    if math.isinf(hi):
        return f"threshold ≥ {lo:.0%} of blocks"
    if math.isinf(lo) or lo <= 0.0:
        return f"threshold ≤ {hi:.0%} of blocks"
    return f"threshold {lo:.0%}-{hi:.0%} of blocks"


# ---- the parity chain -------------------------------------------------------

#: The stack's fixed stage headers with their `in -> out` type chips, in
#: order. A tuple of pairs rather than a dict so the header row iterates it.
STAGE_CHIPS: tuple[tuple[Stage, str], ...] = (
    (Stage.SPATIAL_PREP, "image -> image"),
    (Stage.EXTRACTION, "image -> block series"),
    (Stage.TEMPORAL_FILTER, "series -> series"),
    (Stage.DETECTION, "series -> events"),
)


@dataclass(frozen=True, slots=True)
class LiveChain:
    """The whole tab-side model: steps plus detector, one value.

    Frozen like everything it contains; the tab holds the current one and
    replaces it on every edit, which is what gives the wizard's
    Cancel-restores-everything its mechanism for free.
    """

    steps: tuple[ChainStep, ...]
    detector: DetectorState
    fps: float = 30.0

    def grades(self) -> tuple[StepGrade, ...]:
        """Every step's status. See `grade`."""
        return grade(self.steps)

    def pipeline(self) -> Pipeline:
        """The runnable node-backed prefix. See `runnable_prefix`."""
        return runnable_prefix(self.steps)

    def detection_reachable(self) -> bool:
        """Whether the detection step exists and the walk reaches it.

        False is what makes the count plot say "no reachable detection step"
        and the summary say "chain incomplete — see the stack".
        """
        for step, step_grade in zip(self.steps, self.grades(), strict=True):
            if step.stage is Stage.DETECTION and step_grade.status is Status.OK:
                return True
        return False

    def without(self, step_id: str) -> LiveChain:
        """The chain minus one step — removal, the operation that can break it."""
        return replace(self, steps=tuple(s for s in self.steps if s.step_id != step_id))

    def reset(self, defaults: LiveChain) -> LiveChain:
        """Parameters-not-structure: this chain's steps, `defaults`' knobs.

        Each surviving step keeps its place and identity; a step whose id
        exists in `defaults` takes the default node parameters, one the user
        inserted keeps its own (there is no default to reset it to). The
        detector always resets — bands cleared, disarmed, D back to one
        second.
        """
        by_id = {s.step_id: s for s in defaults.steps}
        steps = tuple(
            replace(s, node=by_id[s.step_id].node) if s.step_id in by_id and s.node else s
            for s in self.steps
        )
        return replace(self, steps=steps, detector=DetectorState.default(self.fps))


def parity_chain(fps: float, *, scale: float = 1.0) -> LiveChain:
    """The tab's default chain: the five parity steps, default knobs, disarmed.

    Node ids are minted fresh per call, which is what keeps two tabs' chains
    from sharing cache identity by accident.
    """
    rescale = Node(filter_id="rescale", version="1.0.0", params={"scale": scale})
    normalize = Node(filter_id="normalize", version="1.0.0", params={"mode": "off"})
    signal = Node(
        filter_id="block_signal",
        version="1.0.0",
        params={"signal": "change_energy", "block": 0, "scale": scale, "fps": fps},
    )
    steps = (
        ChainStep(
            step_id="rescale",
            title="Rescale",
            stage=Stage.SPATIAL_PREP,
            kind_in=ChainKind.IMAGE,
            kind_out=ChainKind.IMAGE,
            node=rescale,
        ),
        ChainStep(
            step_id="normalize",
            title="Normalize",
            stage=Stage.SPATIAL_PREP,
            kind_in=ChainKind.IMAGE,
            kind_out=ChainKind.IMAGE,
            node=normalize,
        ),
        ChainStep(
            step_id="block_signal",
            title="Block signal",
            stage=Stage.EXTRACTION,
            kind_in=ChainKind.IMAGE,
            kind_out=ChainKind.BLOCK_SERIES,
            node=signal,
        ),
        ChainStep(
            step_id="morlet_band",
            title="Morlet band",
            stage=Stage.TEMPORAL_FILTER,
            kind_in=ChainKind.BLOCK_SERIES,
            kind_out=ChainKind.BLOCK_SERIES,
        ),
        ChainStep(
            step_id="windowed_count",
            title="Windowed count",
            stage=Stage.DETECTION,
            kind_in=ChainKind.BLOCK_SERIES,
            kind_out=ChainKind.EVENTS,
        ),
    )
    return LiveChain(steps=steps, detector=DetectorState.default(fps), fps=fps)
