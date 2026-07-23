from __future__ import annotations

import json
import os
import subprocess
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path

import pytest

from antscihub_sieve.application.assets import AssetService


def test_gui_launcher_opens_the_window_maximized(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import PyQt6.QtWidgets
    import antscihub_sieve.gui.main as gui_main
    import antscihub_sieve.gui.main_window as main_window
    calls: list[str] = []

    class Application:
        def __init__(self, argv) -> None: pass  # type: ignore[no-untyped-def]
        def setApplicationName(self, name: str) -> None: pass
        def exec(self) -> int: return 0

    class Window:
        def showMaximized(self) -> None: calls.append("maximized")

    with monkeypatch.context() as patch:
        patch.setattr(PyQt6.QtWidgets, "QApplication", Application)
        patch.setattr(main_window, "MainWindow", Window)
        assert gui_main.main() == 0
    assert calls == ["maximized"]


def make_child(video: Path, output: Path, *, label: str = "rep6") -> dict:  # type: ignore[type-arg]
    from antscihub_sieve.application.derivation import DerivationService
    from antscihub_sieve.application.layouts import LayoutService
    assets = AssetService(); assets.initialize(video, label="parent"); layouts = LayoutService(assets)
    region = layouts.add(video, [1, 1, 12, 10], label)["region"]
    return DerivationService(assets, layouts).run(
        video, region_ids=[region["region_id"]], out=output,
    )["children"][0]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([os.sys.executable, "-m", "antscihub_sieve.cli.main", *args], text=True, capture_output=True)


def test_headless_cli_does_not_import_qt() -> None:
    completed = subprocess.run(
        [
            os.sys.executable,
            "-c",
            (
                "import sys; import antscihub_sieve.cli.main; "
                "assert not any(name.startswith('PyQt6') for name in sys.modules)"
            ),
        ],
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("args", [("asset", "inspect"), ("asset", "init"), ("asset", "verify"), ("lineage", "show"), ("lineage", "parent"),
    ("layout", "inspect"), ("layout", "add"), ("layout", "update"), ("layout", "rename"), ("layout", "remove"), ("layout", "clear"),
    ("layout", "import"), ("layout", "export"), ("layout", "validate"), ("media", "probe"), ("media", "frame"), ("media", "benchmark"), ("derive",), ("derive", "verify")])
def test_required_commands_have_help(args: tuple[str, ...]) -> None:
    completed = run_cli(*args, "--help"); assert completed.returncode == 0 and "usage:" in completed.stdout


def test_cli_json_stdout_and_invalid_usage(video: Path, tmp_path: Path) -> None:
    initialized = run_cli("asset", "init", str(video), "--label", "source", "--json")
    asset = json.loads(initialized.stdout)["asset"]
    assert initialized.returncode == 0 and "kind" not in asset and asset["lineage"]["parent"] is None and initialized.stderr == ""
    frame = run_cli("media", "frame", str(video), "--frame", "0", "--out", str(tmp_path / "frame.png"), "--json")
    assert frame.returncode == 0 and json.loads(frame.stdout)["frame"] == 0 and (tmp_path / "frame.png").read_bytes().startswith(b"\x89PNG")
    invalid = run_cli("layout", "add", str(video), "--box", "bad", "--json"); assert invalid.returncode == 2


def test_media_benchmark_is_a_user_facing_estimate(video: Path) -> None:
    AssetService().initialize(video, label="benchmark source")
    completed = run_cli(
        "media", "benchmark", str(video),
        "--iterations", "1", "--sequential-frames", "3", "--json",
    )
    assert completed.returncode == 0 and completed.stderr == ""
    result = json.loads(completed.stdout)
    assert result["kind"] == "media_performance_estimate"
    assert result["asset"]["asset_id"]
    assert result["representation"] == {
        "kind": "display",
        "max_width": 1280,
        "decoded_width": 18,
        "decoded_height": 14,
    }
    assert result["measurements"]["adjacent_sequential_read"]["count"] == 2
    assert isinstance(result["estimate"]["keeps_up_with_native_rate"], bool)

    human = run_cli(
        "media", "benchmark", str(video),
        "--iterations", "1", "--sequential-frames", "2",
    )
    assert human.returncode == 0
    assert "Media performance estimate:" in human.stdout
    assert "Media service fits the native frame budget:" in human.stdout
    assert "excludes GUI paint" in human.stdout


def test_frame_view_letterbox_mapping_stamp_and_created_immutability(qtbot, video: Path) -> None:  # type: ignore[no-untyped-def]
    from PyQt6.QtCore import QPoint, Qt
    from PyQt6.QtTest import QTest
    from antscihub_sieve.gui.frame_view import FrameView
    view = FrameView(); view.resize(400, 400); qtbot.addWidget(view); view.show(); view.set_frame(bytes([0] * 18 * 14 * 3), 18, 14)
    created: list[list[int]] = []; moved: list[tuple[str, list[int]]] = []; opened: list[int] = []
    view.region_created.connect(created.append); view.region_moved.connect(lambda rid, box: moved.append((rid, box))); view.child_open_requested.connect(opened.append)
    image_rect = view._image_rect(); assert image_rect.top() > 0 and view._to_source(QPoint(2, 2)) is None
    tiny_start = image_rect.topLeft().toPoint() + QPoint(20, 20); tiny_end = tiny_start + QPoint(2, 2)
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=tiny_start); QTest.mouseMove(view, tiny_end); QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=tiny_end)
    assert created == []
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=image_rect.topLeft().toPoint() + QPoint(10, 10)); QTest.mouseMove(view, image_rect.bottomRight().toPoint() - QPoint(10, 10)); QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=image_rect.bottomRight().toPoint() - QPoint(10, 10))
    assert created and created[0][0] < created[0][2] and created[0][1] < created[0][3]
    draft = {"region_id": "r", "label": "rep1", "box_xyxy": [2, 2, 8, 7], "color": "#ff5a5a"}; child = {"region_snapshot": {"region_id": "c", "label": "made", "box_xyxy": [10, 2, 17, 8], "color": "#ffd24a"}}
    view.set_layout([draft], [child], None); view.stamp_enabled = True
    center = view._to_view_rect([0, 0, 1, 1]).center().toPoint(); QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=center)
    assert created[-1][2] - created[-1][0] == 6 and created[-1][3] - created[-1][1] == 5
    child_center = view._to_view_rect(child["region_snapshot"]["box_xyxy"]).center().toPoint(); QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=child_center); assert opened == [0] and moved == []
    view.select("c"); stamp_point = view._to_view_rect([9, 12, 10, 13]).center().toPoint(); QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=stamp_point)
    assert created[-1][2] - created[-1][0] == 7 and created[-1][3] - created[-1][1] == 6


def test_frame_views_retain_zero_copy_rgb_storage(qtbot) -> None:  # type: ignore[no-untyped-def]
    import gc

    from antscihub_sieve.gui.frame_view import FrameView
    from antscihub_sieve.gui.isolate_player import IsolatePlayer

    for view in (FrameView(), IsolatePlayer()):
        qtbot.addWidget(view)
        raw = bytes([10, 20, 30] * 4)
        view.set_frame(raw, 2, 2)
        assert view._frame_bytes is raw
        del raw
        gc.collect()
        color = view.image.pixelColor(0, 0)
        assert (color.red(), color.green(), color.blue()) == (10, 20, 30)


def test_gui_opens_unknown_video_without_classification_prompt(qtbot, video: Path) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.gui.replicate_workspace import ReplicateWorkspace
    workspace = ReplicateWorkspace(); qtbot.addWidget(workspace); workspace.show(); workspace.open_asset(str(video))
    qtbot.waitUntil(lambda: workspace.view.image is not None, timeout=5000)
    asset = workspace.asset_info["asset"]
    assert asset["label"] == video.stem and "kind" not in asset
    assert asset["lineage"] == {"parent": None, "derivation": None, "ancestors": []}
    assert video.with_suffix(".asset.json").exists()
    workspace.toggle_play(); qtbot.waitUntil(lambda: workspace.current_frame >= 2, timeout=5000)
    workspace.close()


def test_gui_marks_crash_interrupted_verification_canceled_on_open(qtbot, video: Path) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.application.layouts import LayoutService
    from antscihub_sieve.gui.replicate_workspace import ReplicateWorkspace
    assets = AssetService(); assets.initialize(video); layouts = LayoutService(assets); region = layouts.add(video, [1, 1, 9, 9])["region"]
    layouts.set_states(video, {region["region_id"]: ("verifying", None)})
    workspace = ReplicateWorkspace(); qtbot.addWidget(workspace); workspace.show(); workspace.open_asset(str(video)); qtbot.waitUntil(lambda: workspace.replicate_table.rowCount() == 1, timeout=5000)
    assert workspace.replicate_table.item(0, 1).text() == "Canceled"
    assert "EXTRACTION_INTERRUPTED" in workspace.replicate_table.item(0, 0).toolTip()
    assert workspace.derive_button.isEnabled()
    assert layouts.load(video)["layout"]["created_children"] == []
    workspace.close()


def test_playback_clock_waits_for_inflight_decode(qtbot) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.gui.replicate_workspace import ReplicateWorkspace
    class Session:
        frame_count = 20
    requested: list[int] = []
    workspace = ReplicateWorkspace(); qtbot.addWidget(workspace); workspace.session = Session()  # type: ignore[assignment]
    workspace._request_frame = requested.append  # type: ignore[method-assign]
    workspace.current_frame = workspace.requested_frame = 4
    workspace._play_tick(); assert requested == [5]
    workspace.requested_frame = 5
    workspace._play_tick(); workspace._play_tick()
    assert requested == [5]
    workspace.current_frame = 5
    workspace._play_tick(); assert requested == [5, 6]
    workspace.session = None; workspace.close()


def test_derivation_dialog_plans_once_without_item_changed_recursion(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.gui.replicate_workspace import DeriveDialog
    class Service:
        def __init__(self) -> None: self.calls = 0
        def plan(self, parent, *, out, profile, region_ids):  # type: ignore[no-untyped-def]
            self.calls += 1
            return {"regions": [{"region_id": region_ids[0], "output_directory": str(Path(out) / "rep1"), "collision": False}]}
    service = Service(); draft = {"region_id": "r1", "label": "rep1", "box_xyxy": [1, 2, 8, 10]}
    dialog = DeriveDialog([draft], str(tmp_path / "parent.mp4"), service)  # type: ignore[arg-type]
    qtbot.addWidget(dialog); dialog.show(); qtbot.waitUntil(dialog.start_button.isEnabled, timeout=2000); qtbot.wait(100)
    assert service.calls == 1
    assert dialog.listing.item(0).toolTip().endswith("rep1")
    assert not dialog.plan_progress.isVisible()
    dialog.close()


def test_create_children_action_is_prominent_with_progress_above_replicates(qtbot) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.gui.replicate_workspace import ReplicateWorkspace
    workspace = ReplicateWorkspace(); qtbot.addWidget(workspace); workspace.resize(1000, 700); workspace.show(); qtbot.wait(50)
    assert workspace.derive_button.minimumWidth() >= 250
    assert workspace.derive_button.height() >= 46
    assert workspace.derive_button.x() > workspace.export_button.x()
    assert not hasattr(workspace, "duplicate_button")
    workspace.busy_overlay.show(); qtbot.wait(20)
    assert workspace.busy_overlay.parentWidget() is workspace.inspector
    assert workspace.busy_overlay.y() < workspace.replicate_table.y()
    assert workspace.busy_overlay.isVisible() and workspace.progress.isVisible() and workspace.cancel_button.isVisible()
    workspace.close()


def test_replicates_splitter_defaults_to_an_even_draggable_split(qtbot) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.gui.replicate_workspace import ReplicateWorkspace
    workspace = ReplicateWorkspace(); qtbot.addWidget(workspace); workspace.resize(1000, 700); workspace.show(); qtbot.wait(50)
    left, right = workspace.splitter.sizes()
    assert abs(left - right) <= 1
    workspace.splitter.setSizes([700, 300]); qtbot.wait(20)
    moved_left, moved_right = workspace.splitter.sizes()
    assert moved_left > moved_right
    workspace.close()


@pytest.mark.parametrize("key", ["Delete", "Backspace"])
def test_delete_keys_remove_the_selected_draft(qtbot, video: Path, monkeypatch, key: str) -> None:  # type: ignore[no-untyped-def]
    from PyQt6.QtGui import QKeySequence
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QMessageBox
    from antscihub_sieve.application.layouts import LayoutService
    from antscihub_sieve.gui.replicate_workspace import ReplicateWorkspace
    assets = AssetService(); assets.initialize(video); layouts = LayoutService(assets); layouts.add(video, [1, 1, 9, 9])
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    workspace = ReplicateWorkspace(); qtbot.addWidget(workspace); workspace.show(); workspace.open_asset(str(video)); qtbot.waitUntil(lambda: workspace.replicate_table.rowCount() == 1, timeout=5000)
    assert workspace.stamp_check.isChecked() and workspace.view.stamp_enabled
    workspace.replicate_table.selectRow(0); workspace.replicate_table.setCurrentCell(0, 0)
    QTest.keyClick(workspace.replicate_table, QKeySequence(key)[0].key())
    qtbot.waitUntil(lambda: workspace.replicate_table.rowCount() == 0, timeout=2000)
    assert layouts.load(video)["layout"]["draft_regions"] == []
    workspace.close()


def test_compact_replicates_table_status_tooltips_and_recursive_open(qtbot, video: Path, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.application.derivation import DerivationService
    from antscihub_sieve.application.layouts import LayoutService
    from antscihub_sieve.gui.replicate_workspace import ReplicateWorkspace
    assets = AssetService(); assets.initialize(video, label="parent"); layouts = LayoutService(assets)
    region = layouts.add(video, [1, 1, 12, 10], "rep1")["region"]
    child = DerivationService(assets, layouts).run(video, region_ids=[region["region_id"]], out=tmp_path / "children")["children"][0]
    layouts.add(child["media_path"], [0, 0, 5, 5], "inner")
    workspace = ReplicateWorkspace(); qtbot.addWidget(workspace); workspace.show(); workspace.open_asset(str(video)); qtbot.waitUntil(lambda: workspace.view.image is not None, timeout=5000)
    table = workspace.replicate_table
    assert [table.horizontalHeaderItem(i).text() for i in range(4)] == ["Replicate", "State", "Children", ""]
    assert table.rowCount() == 1 and [table.item(0, i).text() for i in range(3)] == ["rep1", "Ready", "1"]
    folder_button = table.cellWidget(0, 3)
    assert folder_button is not None and folder_button.isEnabled() and folder_button.text() == ""
    opened_urls = []
    monkeypatch.setattr("antscihub_sieve.gui.replicate_workspace.QDesktopServices.openUrl", lambda url: opened_urls.append(url) or True)
    folder_button.click()
    assert Path(opened_urls[0].toLocalFile()).resolve() == Path(child["media_path"]).parent.resolve()
    assert table.item(0, 0).foreground().color().name() == region["color"]
    tooltip = table.item(0, 0).toolTip(); assert "Size:" in tooltip and "Coordinates:" in tooltip and "Asset id:" in tooltip and "Path:" in tooltip
    assert workspace.summary_label.text() == "1 replicate\n1 ready"
    class ActiveDerivation:
        def cancel(self) -> None: pass
        def wait(self) -> None: pass
    table.selectRow(0); table.setCurrentCell(0, 0); assert workspace.view.selected_id == region["region_id"]
    workspace.derive_thread = ActiveDerivation()  # type: ignore[assignment]
    workspace._derive_parent = str(video); workspace._update_action_buttons()
    assert workspace.open_child_button.isEnabled()
    workspace.open_child_index(0); qtbot.waitUntil(lambda: workspace.asset_info["asset"]["asset_id"] == child["asset"]["asset_id"], timeout=5000)
    assert workspace.session.path.resolve() == Path(child["media_path"]).resolve()
    workspace.derive_thread = None; workspace._derive_parent = None
    workspace.open_asset(str(video)); qtbot.waitUntil(lambda: workspace.asset_info["asset"]["label"] == "parent", timeout=5000)
    workspace.layout_doc["created_children"][0]["child"]["location_hints"] = ["missing/video.asset.json"]; layouts.save(video, workspace.layout_doc); workspace._refresh_layout()
    assert not table.cellWidget(0, 3).isEnabled()
    assert [table.item(0, i).text() for i in range(3)] == ["rep1", "Missing", "—"]
    assert workspace.summary_label.text() == "1 replicate\n1 missing"
    table.selectRow(0); table.setCurrentCell(0, 0)
    assert workspace.locate_child_button.isEnabled()
    assert workspace.delete_button.isEnabled()
    workspace.close()


def test_delete_removes_a_missing_child_record_without_deleting_its_files(qtbot, video: Path, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from PyQt6.QtWidgets import QMessageBox
    from antscihub_sieve.application.derivation import DerivationService
    from antscihub_sieve.application.layouts import LayoutService
    from antscihub_sieve.gui.replicate_workspace import ReplicateWorkspace
    assets = AssetService(); assets.initialize(video, label="parent"); layouts = LayoutService(assets)
    region = layouts.add(video, [1, 1, 12, 10], "rep1")["region"]
    child = DerivationService(assets, layouts).run(video, region_ids=[region["region_id"]], out=tmp_path / "children")["children"][0]
    child_media = Path(child["media_path"]); child_sidecar = Path(child["asset_path"])
    layout = layouts.load(video)["layout"]; layout["created_children"][0]["child"]["location_hints"] = ["missing/video.asset.json"]; layouts.save(video, layout)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    workspace = ReplicateWorkspace(); qtbot.addWidget(workspace); workspace.show(); workspace.open_asset(str(video))
    qtbot.waitUntil(lambda: workspace.replicate_table.rowCount() == 1, timeout=5000)
    workspace.replicate_table.selectRow(0); workspace.replicate_table.setCurrentCell(0, 0)
    workspace.delete_button.click()
    assert workspace.replicate_table.rowCount() == 0
    assert layouts.load(video)["layout"]["created_children"] == []
    assert child_media.exists() and child_sidecar.exists()
    workspace.close()


def test_opening_asset_updates_both_workflow_tabs(qtbot, video: Path) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.gui.main_window import MainWindow
    window = MainWindow(); qtbot.addWidget(window); window.show(); window.open_asset(video)
    qtbot.waitUntil(lambda: window.replicates_tab.view.image is not None, timeout=5000)
    active = window.controller.active_asset
    assert active is not None
    assert window.replicates_tab.asset_info["asset"]["asset_id"] == active.asset_id
    assert window.isolate_tab.session.asset == active
    qtbot.waitUntil(lambda: window.isolate_tab.player.image is not None, timeout=5000)
    assert not hasattr(window, "asset_label")
    assert not hasattr(window, "meta_label")
    assert window.windowTitle() == (
        f"SIEVE - {'/'.join(Path(active.video_path).parts[-3:])} · "
        f"{active.width}×{active.height} · {active.fps:.3f} fps · "
        f"{active.duration_seconds:.3f}s"
    )
    window.replicates_tab.close(); window.close()


def test_file_and_edit_menus_expose_open_undo_and_redo(qtbot) -> None:  # type: ignore[no-untyped-def]
    from PyQt6.QtGui import QKeySequence
    from antscihub_sieve.gui.main_window import MainWindow
    window = MainWindow(); qtbot.addWidget(window)
    assert not hasattr(window, "open_button")
    assert window.menuBar().actions()[0].text() == "&File"
    assert window.menuBar().actions()[1].text() == "&Edit"
    assert window.open_action.text() == "&Open…"
    assert window.open_action.shortcut().matches(QKeySequence(QKeySequence.StandardKey.Open)) == QKeySequence.SequenceMatch.ExactMatch
    assert not window.open_last_action.isEnabled()
    assert window.open_last_action.text() == "Open &Last — No recent file"
    assert window.recent_list.item(0).text() == "No recent files"
    assert window.undo_action.text().startswith("&Undo")
    assert window.redo_action.text().startswith("&Redo")
    window.replicates_tab.close(); window.close()


def test_recent_files_are_persisted_scrollable_and_open_last_names_the_file(qtbot, video: Path, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    from PyQt6.QtCore import QPoint, QSettings
    from antscihub_sieve.gui.main_window import MainWindow
    settings = QSettings(str(tmp_path / "recents.ini"), QSettings.Format.IniFormat)
    older = []
    for index in range(12):
        path = tmp_path / f"folder-{index}" / f"clip-{index}.mp4"
        path.parent.mkdir()
        path.touch()
        older.append(str(path))
    settings.setValue(MainWindow.RECENT_FILES_KEY, older)

    window = MainWindow(settings); qtbot.addWidget(window); window.show(); qtbot.wait(20)
    assert window.recent_list.count() == 12
    window.recent_menu.popup(window.mapToGlobal(QPoint(20, 20))); qtbot.wait(20)
    assert window.recent_list.verticalScrollBar().maximum() > 0
    window.recent_menu.close()
    assert "clip-0.mp4" in window.open_last_action.text()
    assert window.open_last_action.toolTip() == older[0]

    window.open_asset(video)
    qtbot.waitUntil(lambda: window.controller.active_asset is not None, timeout=5000)
    assert window._recent_files()[0] == str(video.resolve())
    assert video.name in window.open_last_action.text()
    window.replicates_tab.close(); window.close()

    reopened = MainWindow(settings); qtbot.addWidget(reopened); reopened.show()
    assert video.name in reopened.open_last_action.text()
    reopened.open_last_action.trigger()
    qtbot.waitUntil(lambda: reopened.controller.active_asset is not None, timeout=5000)
    assert Path(reopened.controller.active_asset.video_path).resolve() == video.resolve()
    reopened.replicates_tab.close(); reopened.close()


def test_ctrl_z_undoes_new_replicate_and_redo_restores_it(qtbot, video: Path) -> None:  # type: ignore[no-untyped-def]
    from PyQt6.QtCore import Qt
    from PyQt6.QtTest import QTest
    from antscihub_sieve.application.layouts import LayoutService
    from antscihub_sieve.gui.main_window import MainWindow
    window = MainWindow(); qtbot.addWidget(window); window.show(); window.open_asset(video)
    qtbot.waitUntil(lambda: window.replicates_tab.view.image is not None, timeout=5000)
    workspace = window.replicates_tab
    workspace._add_region([1, 1, 9, 9])
    created = LayoutService().load(video)["layout"]["draft_regions"]
    assert len(created) == 1 and window.undo_action.isEnabled()

    QTest.keyClick(window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    qtbot.waitUntil(lambda: workspace.replicate_table.rowCount() == 0, timeout=2000)
    assert LayoutService().load(video)["layout"]["draft_regions"] == []
    assert window.redo_action.isEnabled()

    window.redo_action.trigger()
    assert LayoutService().load(video)["layout"]["draft_regions"] == created
    assert workspace.replicate_table.rowCount() == 1
    workspace.close(); window.close()


def test_child_click_direct_open_and_parent_navigation_share_identical_asset(qtbot, video: Path, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.gui.main_window import MainWindow
    child = make_child(video, tmp_path / "children")
    window = MainWindow(); qtbot.addWidget(window); window.show(); window.open_asset(video)
    qtbot.waitUntil(lambda: window.replicates_tab.replicate_table.rowCount() == 1, timeout=5000)

    table = window.replicates_tab.replicate_table
    table.selectRow(0); table.setCurrentCell(0, 0)
    table.cellDoubleClicked.emit(0, 0)
    qtbot.waitUntil(lambda: window.controller.active_asset.asset_id == child["asset"]["asset_id"], timeout=5000)
    clicked_snapshot = window.controller.active_asset
    assert window.isolate_tab.session.asset == clicked_snapshot
    assert window.isolate_tab.session.media.path.resolve() == Path(child["media_path"]).resolve()
    assert window.replicates_tab.asset_info["asset"]["asset_id"] == clicked_snapshot.asset_id

    window.open_asset(video)
    qtbot.waitUntil(lambda: window.controller.active_asset.label == "parent", timeout=5000)
    window.open_asset(child["asset_path"])
    qtbot.waitUntil(lambda: window.controller.active_asset.asset_id == child["asset"]["asset_id"], timeout=5000)
    assert window.controller.active_asset == clicked_snapshot

    window.open_parent()
    qtbot.waitUntil(lambda: window.controller.active_asset.label == "parent", timeout=5000)
    assert window.replicates_tab.asset_info["asset"]["asset_id"] == window.controller.active_asset.asset_id
    assert window.isolate_tab.session.asset == window.controller.active_asset
    window.replicates_tab.close(); window.close()


def test_switching_workflow_tabs_does_not_change_active_asset(qtbot, video: Path) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.gui.main_window import MainWindow
    window = MainWindow(); qtbot.addWidget(window); window.show(); window.open_asset(video)
    qtbot.waitUntil(lambda: window.replicates_tab.view.image is not None, timeout=5000)
    active = window.controller.active_asset
    changes: list[object] = []
    window.controller.active_asset_changed.connect(changes.append)
    window.tabs.setCurrentWidget(window.isolate_tab)
    window.tabs.setCurrentWidget(window.replicates_tab)
    assert window.controller.active_asset is active
    assert changes == []
    window.replicates_tab.close(); window.close()


def test_active_asset_state_is_immutable_metadata_without_replicate_boxes(qtbot, video: Path) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.application.active_asset import ActiveAssetController
    controller = ActiveAssetController(); asset = controller.open_asset(video)
    flattened = repr(asdict(asset)).casefold()
    assert "box" not in flattened and "layout" not in flattened and "row" not in flattened
    assert "decoder" not in flattened and "result" not in flattened
    with pytest.raises(FrozenInstanceError):
        asset.label = "changed"  # type: ignore[misc]


def test_workflow_tabs_share_only_the_active_asset_controller(qtbot) -> None:  # type: ignore[no-untyped-def]
    import inspect
    from antscihub_sieve.gui.main_window import MainWindow
    from antscihub_sieve.gui.isolate_tab import IsolateTab
    from antscihub_sieve.gui.replicate_workspace import ReplicateWorkspace
    window = MainWindow(); qtbot.addWidget(window)
    assert window.replicates_tab.controller is window.controller
    assert window.isolate_tab._controller is window.controller
    assert not hasattr(window.replicates_tab, "isolate_tab")
    assert not hasattr(window.isolate_tab, "replicates_tab")
    assert "IsolateTab" not in inspect.getsource(ReplicateWorkspace)
    assert "ReplicateWorkspace" not in inspect.getsource(IsolateTab)
    window.replicates_tab.close(); window.close()


def test_second_workflow_tab_is_visibly_named_isolate(qtbot) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.gui.main_window import MainWindow
    window = MainWindow(); qtbot.addWidget(window)
    assert window.tabs.tabText(1) == "Isolate"
    assert window.isolate_tab.channels_empty.text() == "No channels added yet."
    window.replicates_tab.close(); window.close()
