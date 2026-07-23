from __future__ import annotations

import threading
import time
from pathlib import Path


def open_isolate(qtbot, video: Path):  # type: ignore[no-untyped-def]
    from antscihub_sieve.application.active_asset import ActiveAssetController
    from antscihub_sieve.gui.isolate_tab import IsolateTab

    controller = ActiveAssetController()
    tab = IsolateTab(controller)
    qtbot.addWidget(tab)
    tab.resize(1000, 700)
    tab.show()
    controller.open_asset(video)
    qtbot.waitUntil(lambda: tab.session.loaded, timeout=5000)
    tab.session.set_window_length(min(2, tab.session.frame_count))
    return tab


def test_compute_publishes_one_channel_and_grid_change_invalidates_it(
    qtbot,
    video: Path,
) -> None:  # type: ignore[no-untyped-def]
    tab = open_isolate(qtbot, video)
    assert tab.compute_intensity_button.isEnabled()
    tab.compute_intensity_button.click()
    qtbot.waitUntil(
        lambda: tab._intensity_worker is None,
        timeout=10_000,
    )
    result = tab._intensity_result
    assert result is not None and result.complete
    assert result.values.shape == (tab.session.window_length, 1, 1)
    assert tab.intensity_panel.isVisible()
    assert not tab.channels_empty.isVisible()
    assert "post-decoder RGB601" in tab.intensity_legend.text()
    assert "sieve.channel.rgb601_intensity.v1" in tab.compute_status.text()

    tab.downsample_spin.setValue(0.5)
    assert tab._intensity_result is None
    assert not tab.intensity_panel.isVisible()
    assert tab.channels_empty.isVisible()
    tab.close()


def test_latest_compute_waits_for_cancelled_worker_exit_before_starting(
    qtbot,
    video: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    import antscihub_sieve.gui.intensity_worker as worker_module

    actual_compute = worker_module.compute_intensity
    first_entered = threading.Event()
    call_count = 0

    def controlled_compute(request, *, cancelled, progress):  # type: ignore[no-untyped-def]
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            first_entered.set()
            while not cancelled():
                time.sleep(0.001)
        return actual_compute(
            request,
            cancelled=cancelled,
            progress=progress,
        )

    monkeypatch.setattr(worker_module, "compute_intensity", controlled_compute)
    tab = open_isolate(qtbot, video)
    tab._compute_intensity()
    qtbot.waitUntil(first_entered.is_set, timeout=5000)
    first_worker = tab._intensity_worker
    assert first_worker is not None and first_worker.isRunning()

    tab._compute_intensity()
    assert tab._pending_intensity is not None
    assert tab._intensity_worker is first_worker
    qtbot.waitUntil(
        lambda: tab._intensity_result is not None,
        timeout=10_000,
    )
    assert call_count == 2
    assert not first_worker.isRunning()
    assert tab._pending_intensity is None
    assert tab._intensity_result is not None
    assert tab._intensity_result.complete
    tab.close()


def test_over_budget_request_reports_exact_bytes_without_channel(
    qtbot,
    video: Path,
) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.application.resources import ExecutionResourcePolicy

    tab = open_isolate(qtbot, video)
    tab.resource_policy = ExecutionResourcePolicy(
        cpu_result_memory_bytes=1,
        gpu_result_memory_bytes=6 * 1024**3,
    )
    tab._compute_intensity()
    qtbot.waitUntil(
        lambda: tab._intensity_worker is None,
        timeout=5000,
    )
    assert tab._intensity_result is None
    assert "RESOURCE_RESULT_MEMORY_EXCEEDED" in tab.compute_status.text()
    assert "Requested" in tab.compute_status.text()
    assert "allowed 1 bytes" in tab.compute_status.text()
    tab.close()


def test_channel_click_seeks_absolute_player_frame(
    qtbot,
    video: Path,
) -> None:  # type: ignore[no-untyped-def]
    from PyQt6.QtCore import QPoint, Qt
    from PyQt6.QtTest import QTest

    tab = open_isolate(qtbot, video)
    tab._compute_intensity()
    qtbot.waitUntil(
        lambda: tab._intensity_result is not None,
        timeout=10_000,
    )
    raster = tab.intensity_raster
    target = raster.rect().adjusted(1, 1, -2, -2)
    QTest.mouseClick(
        raster,
        Qt.MouseButton.LeftButton,
        pos=QPoint(
            target.left() + (target.width() * 3 // 4),
            target.center().y(),
        ),
    )
    result = tab._intensity_result
    assert result is not None
    expected_offset = min(
        result.values.shape[0] - 1,
        (target.width() * 3 // 4) * result.values.shape[0] // target.width(),
    )
    assert tab.session.current_frame == result.processed_start + expected_offset
    tab.close()
