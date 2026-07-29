

































from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import NDArray

from sieve.core.pipeline_model import DetectorSettings, Edge, Node, Pipeline
from sieve.core.wavelet import band_indices, default_freqs




from sieve.detect import DetectorUpdate, detect
from sieve.filters.block_signal import resolve_block

FloatArray = NDArray[np.floating[Any]]


SIGNAL_LABELS: dict[str, str] = {
    "change_energy": "change energy (Jtt)",
    "flow_speed": "LK optical flow",
    "coherence": "coherence (0-1)",
    "flow_agreement": "flow agreement (0-1)",
}


class ChainKind(StrEnum):







    IMAGE = "image"
    BLOCK_SERIES = "block series"
    EVENTS = "events"


class Stage(StrEnum):


    SPATIAL_PREP = "spatial prep"
    EXTRACTION = "signal extraction"
    TEMPORAL_FILTER = "temporal filter"
    DETECTION = "detection"


class Status(StrEnum):


    OK = "ok"
    CONFLICT = "conflict"
    UNREACHED = "unreached"


@dataclass(frozen=True, slots=True)
class ChainStep:








    step_id: str
    title: str
    stage: Stage
    kind_in: ChainKind
    kind_out: ChainKind
    node: Node | None = None


@dataclass(frozen=True, slots=True)
class StepGrade:


    status: Status



    message: str = ""


def grade(steps: tuple[ChainStep, ...]) -> tuple[StepGrade, ...]:








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











    freq_band: tuple[float, float] = (0.0, math.inf)

    value_band: tuple[float, float] = (-math.inf, math.inf)


    count_frac: tuple[float, float] | None = None

    window_frames: int = 30
    centered: bool = True


    solo_block: int | None = None

    @property
    def armed(self) -> bool:

        return self.count_frac is not None

    @classmethod
    def default(cls, fps: float) -> DetectorState:

        return cls(window_frames=max(1, round(fps)))

    def as_settings_changes(self) -> dict[str, Any]:







        return {
            "freq_band": self.freq_band,
            "value_band": self.value_band,
            "count_frac": self.count_frac,
            "window_frames": self.window_frames,
            "centered": self.centered,
        }

    def to_settings(self) -> DetectorSettings:









        return DetectorSettings(**self.as_settings_changes())

    @classmethod
    def from_settings(cls, settings: DetectorSettings, *, solo_block: int | None) -> DetectorState:






        return cls(
            freq_band=settings.freq_band,
            value_band=settings.value_band,
            count_frac=settings.count_frac,
            window_frames=settings.window_frames,
            centered=settings.centered,
            solo_block=solo_block,
        )


def recompute(
    series: FloatArray,
    fps: float,
    state: DetectorState,
    *,
    start_index: int = 0,
    band_power: NDArray[np.float32] | None = None,
    workers: int,
) -> DetectorUpdate:








    return detect(
        series,
        fps,
        state.to_settings(),
        start_index=start_index,
        band_power=band_power,
        workers=workers,
    )


def snapped_band_label(freq_band: tuple[float, float], fps: float) -> str:






    freqs = default_freqs(fps)
    i, j = band_indices(freqs, freq_band[0], freq_band[1])
    return f"band {freqs[i]:.2f}-{freqs[j - 1]:.2f} Hz"


def caption_for(step: ChainStep, detector: DetectorState, fps: float) -> str:










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

    if detector.count_frac is None:
        return "threshold off"
    lo, hi = detector.count_frac
    if math.isinf(hi):
        return f"threshold ≥ {lo:.0%} of blocks"
    if math.isinf(lo) or lo <= 0.0:
        return f"threshold ≤ {hi:.0%} of blocks"
    return f"threshold {lo:.0%}-{hi:.0%} of blocks"






STAGE_CHIPS: tuple[tuple[Stage, str], ...] = (
    (Stage.SPATIAL_PREP, "image -> image"),
    (Stage.EXTRACTION, "image -> block series"),
    (Stage.TEMPORAL_FILTER, "series -> series"),
    (Stage.DETECTION, "series -> events"),
)


@dataclass(frozen=True, slots=True)
class LiveChain:







    steps: tuple[ChainStep, ...]
    detector: DetectorState
    fps: float = 30.0

    def grades(self) -> tuple[StepGrade, ...]:

        return grade(self.steps)

    def pipeline(self) -> Pipeline:

        return runnable_prefix(self.steps)

    def detection_reachable(self) -> bool:





        for step, step_grade in zip(self.steps, self.grades(), strict=True):
            if step.stage is Stage.DETECTION and step_grade.status is Status.OK:
                return True
        return False

    def without(self, step_id: str) -> LiveChain:

        return replace(self, steps=tuple(s for s in self.steps if s.step_id != step_id))

    def reset(self, defaults: LiveChain) -> LiveChain:








        by_id = {s.step_id: s for s in defaults.steps}
        steps = tuple(
            replace(s, node=by_id[s.step_id].node) if s.step_id in by_id and s.node else s
            for s in self.steps
        )
        return replace(self, steps=steps, detector=DetectorState.default(self.fps))


def parity_chain(fps: float, *, scale: float = 1.0) -> LiveChain:





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
