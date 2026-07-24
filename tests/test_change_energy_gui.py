from __future__ import annotations

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


def test_change_energy_selection_computes_only_selected_result_and_overlay(
    qtbot,
    video: Path,
) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.application.change_energy import ChangeEnergyResult

    tab = open_isolate(qtbot, video)
    tab.channel_combo.setCurrentIndex(1)
    assert tab.selected_channel == "change_energy"
    assert tab._intensity_worker is None
    tab.compute_intensity_button.click()
    qtbot.waitUntil(lambda: tab._intensity_worker is None, timeout=10_000)
    result = tab._selected_result
    assert isinstance(result, ChangeEnergyResult)
    assert result.complete
    assert tab._intensity_result is None
    assert tab._change_energy_result is result
    assert "sieve.channel.rgb601_change_energy.v1" in tab.intensity_legend.text()
    assert result.temporal_valid[0] == (
        0 if result.processed_start == 0 else 1
    )
    if tab.player.displayed_frame == 0:
        assert tab.player.channel_overlay is None
        tab.session.step(1)
        qtbot.waitUntil(lambda: tab.player.displayed_frame == 1, timeout=5000)
    assert tab.player.channel_overlay is not None
    assert (
        tab.player.channel_overlay.absolute_frame
        == tab.player.displayed_frame
    )
    tab.close()


def test_channel_switch_reuses_single_newest_only_worker(
    qtbot,
    video: Path,
) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.application.change_energy import ChangeEnergyResult

    tab = open_isolate(qtbot, video)
    tab.compute_intensity_button.click()
    qtbot.waitUntil(lambda: tab._selected_result is not None, timeout=10_000)
    old = tab._selected_result
    tab.channel_combo.setCurrentIndex(1)
    assert tab._selected_result is None
    qtbot.waitUntil(lambda: tab._selected_result is not None, timeout=10_000)
    assert isinstance(tab._selected_result, ChangeEnergyResult)
    assert tab._selected_result is not old
    assert tab._pending_intensity is None
    tab.close()


def test_overlay_is_gated_by_authoritative_displayed_frame(
    qtbot,
    video: Path,
) -> None:  # type: ignore[no-untyped-def]
    tab = open_isolate(qtbot, video)
    tab.compute_intensity_button.click()
    qtbot.waitUntil(lambda: tab._selected_result is not None, timeout=10_000)
    overlay = tab.player.channel_overlay
    assert overlay is not None
    tab.player.set_frame(
        bytes(tab.player._frame_bytes or b""),
        tab.player.frame_size[0],
        tab.player.frame_size[1],
        overlay.absolute_frame + 1,
    )
    assert tab.player.channel_overlay is None
    tab.close()


def test_density_panel_excludes_temporally_invalid_frame_zero(
    qtbot,
    video: Path,
) -> None:  # type: ignore[no-untyped-def]
    tab = open_isolate(qtbot, video)
    tab.channel_combo.setCurrentIndex(1)
    tab.session.set_window_start(0)
    tab.session.set_window_length(min(2, tab.session.frame_count))
    tab.compute_intensity_button.click()
    qtbot.waitUntil(lambda: tab._selected_result is not None, timeout=10_000)
    raster = tab.intensity_raster
    assert raster._density_count is not None
    assert int(raster._density_count[:, 0].sum()) == 0
    if raster._density_count.shape[1] > 1:
        assert int(raster._density_count[:, 1].sum()) > 0
    tab.close()
