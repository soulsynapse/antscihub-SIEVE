"""Preferences stop at the view boundary: results and keys do not read them."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QCoreApplication, QSettings

from sieve.backend.dispatch import Backend, KernelRegistry, kernel
from sieve.core.filter_base import ArraySpec, CostEstimate, ElementRelation, ParamsBase
from sieve.core.filter_registry import FilterRegistry, register_filter
from sieve.core.pipeline_model import ClipRange, Node, Pipeline
from sieve.core.types import ChannelSpec, Frame, WorkUnits
from sieve.gui.preferences import Preferences
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import execute
from sieve.pipeline.plan import ExecutionPlan

pytestmark = pytest.mark.gui

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = "footage|1|2"
SPAN = ClipRange(start=3, end=6)
COST = CostEstimate(work_per_megapixel=WorkUnits(1.0))
SHELF = FilterRegistry()
KERNELS = KernelRegistry()

FrameSignature = tuple[int, tuple[int, ...], bytes]
RunSignature = tuple[dict[str, str], tuple[FrameSignature, ...]]


@register_filter(
    filter_id="preference_probe",
    version="1.0.0",
    summary="Adds an amount to every pixel.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    element=ElementRelation.PRESERVED,
    cost=COST,
    registry=SHELF,
)
class PreferenceProbeParams(ParamsBase):
    amount: int = 7


@kernel(PreferenceProbeParams, Backend.CPU, registry=KERNELS)
def preference_probe_cpu(frame: Frame, params: PreferenceProbeParams) -> Frame:
    return Frame(
        data=frame.data + np.uint8(params.amount),
        index=frame.index,
        channels=frame.channels,
    )


class ProbeSource:
    def read(self, index: int) -> Frame:
        data = np.full((4, 5), index, dtype=np.uint8)
        return Frame(data=data, index=index, channels=ChannelSpec.GRAY)


@pytest.fixture
def default_preferences(qapp: object, tmp_path: Path) -> Iterator[Preferences]:
    """Point ambient `Preferences()` reads at a temporary settings home."""
    del qapp
    original_format = QSettings.defaultFormat()
    original_org = QCoreApplication.organizationName()
    original_app = QCoreApplication.applicationName()
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    QCoreApplication.setOrganizationName("antscihub-sieve-tests")
    QCoreApplication.setApplicationName("preference-boundary")
    settings = QSettings()
    settings.clear()
    settings.sync()
    try:
        yield Preferences()
    finally:
        settings.clear()
        settings.sync()
        QCoreApplication.setOrganizationName(original_org)
        QCoreApplication.setApplicationName(original_app)
        QSettings.setDefaultFormat(original_format)


def test_preferences_have_one_qsettings_home() -> None:
    users: list[str] = []
    for path in (REPO_ROOT / "src" / "sieve").rglob("*.py"):
        if "QSettings" in path.read_text(encoding="utf-8"):
            users.append(path.relative_to(REPO_ROOT).as_posix())

    assert users == ["src/sieve/gui/preferences.py"]


def test_scrambling_every_preference_leaves_results_and_cache_keys_unchanged(
    default_preferences: Preferences, tmp_path: Path
) -> None:
    pipeline = Pipeline(
        nodes=(
            Node(
                node_id="probe",
                filter_id="preference_probe",
                version="1.0.0",
                params={"amount": 11},
            ),
        )
    )
    scrambles = _scrambles(tmp_path)
    assert set(scrambles) == _preference_names()

    _apply_scramble(default_preferences, scrambles, side=0)
    first = _run_signature(pipeline)
    _apply_scramble(default_preferences, scrambles, side=1)
    second = _run_signature(pipeline)

    assert second == first


def _scrambles(tmp_path: Path) -> Mapping[str, tuple[object, object]]:
    return {
        "adaptive_scrub": (False, True),
        "coarse_interval_seconds": (0.25, 10.0),
        "last_video": (tmp_path / "first.mp4", tmp_path / "second.mp4"),
        "proxy_width": (320, 3840),
        "render_fed_playback": (False, True),
        "viewport_luma": (True, False),
        "window_seconds": (0.01, 24.0 * 60.0 * 60.0),
        "write_through_project": (False, True),
    }


def _preference_names() -> set[str]:
    return {
        name
        for name, member in vars(Preferences).items()
        if isinstance(member, property) and member.fset is not None
    }


def _apply_scramble(
    preferences: Preferences, scrambles: Mapping[str, tuple[object, object]], *, side: int
) -> None:
    for name, pair in scrambles.items():
        setattr(preferences, name, pair[side])


def _run_signature(pipeline: Pipeline) -> RunSignature:
    plan = ExecutionPlan.build(
        Dag.build(pipeline, SHELF),
        source=SOURCE,
        span=SPAN,
        backend=Backend.CPU,
    )
    frames: list[FrameSignature] = []
    for result in execute(plan, ProbeSource(), kernels=KERNELS):
        frame = result["probe"]
        frames.append((int(result.index), tuple(frame.data.shape), frame.data.tobytes()))
    return dict(plan.keys), tuple(frames)
