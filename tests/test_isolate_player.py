from __future__ import annotations

import subprocess
from pathlib import Path


class RequestedFrames:
    def __init__(self) -> None:
        self.frames: list[int] = []

    def request(self, frame: int) -> None:
        self.frames.append(frame)


def configured_session(qtbot, *, frames: int = 300, fps_num: int = 30, fps_den: int = 1):  # type: ignore[no-untyped-def]
    from antscihub_sieve.gui.isolate_session import IsolateSession
    session = IsolateSession()
    decoder = RequestedFrames()
    session.media = object()  # type: ignore[assignment]
    session.decoder = decoder  # type: ignore[assignment]
    session.frame_count = frames
    session.fps_num = fps_num
    session.fps_den = fps_den
    session.window_start = 0
    session.window_stop = min(frames, 300)
    session.current_frame = session.window_start
    session.displayed_frame = session.current_frame
    return session, decoder


def test_real_asset_initial_window_and_short_asset(qtbot, video: Path, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.application.active_asset import ActiveAssetController
    from antscihub_sieve.gui.isolate_session import IsolateSession
    long_video = tmp_path / "long.mkv"
    completed = subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
            "testsrc2=size=18x14:rate=6:duration=12",
            "-c:v", "ffv1", "-pix_fmt", "bgr0", str(long_video),
        ],
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    controller = ActiveAssetController()
    session = IsolateSession()
    session.open_asset(controller.open_asset(long_video))
    assert (session.window_start, session.window_stop) == (0, 60)
    assert session.current_frame == 0 and not session.playing
    session.toggle_play()
    assert session.playing
    session.open_asset(controller.open_asset(video))
    assert (session.window_start, session.window_stop) == (0, session.frame_count)
    assert session.current_frame == 0 and not session.playing
    session.close()


def test_window_settling_preserves_length_and_clamps_cursor(qtbot) -> None:  # type: ignore[no-untyped-def]
    session, decoder = configured_session(qtbot)
    session.window_start, session.window_stop = 100, 160
    session.current_frame = 150
    session.set_window_start(295)
    assert (session.window_start, session.window_stop) == (240, 300)
    assert session.current_frame == 240
    session.set_window_length(10)
    assert (session.window_start, session.window_stop) == (240, 250)
    assert session.current_frame == 240
    session.current_frame = 249
    session.set_window_length(2)
    assert (session.window_start, session.window_stop) == (240, 242)
    assert session.current_frame == 241
    assert decoder.frames[-1] == 241


def test_session_model_does_not_encode_the_ui_sixty_second_cap(qtbot) -> None:  # type: ignore[no-untyped-def]
    session, _ = configured_session(qtbot, frames=10_000, fps_num=30)
    session.window_start, session.window_stop = 0, 300
    session.set_window_length(3_600)
    assert session.window_length == 3_600
    assert session.ui_maximum_length() == 1_800


def test_rational_timebase_and_half_open_window(qtbot) -> None:  # type: ignore[no-untyped-def]
    session, _ = configured_session(
        qtbot, frames=90_000, fps_num=30_000, fps_den=1_001
    )
    assert session.seconds_for_frame(30_000) == 1001.0
    assert session.frames_for_seconds(1.0) == 30
    assert session.frame_at_seconds(0.0) == 0
    session.window_start, session.window_stop = 10, 20
    session.request_frame(20)
    assert session.current_frame == 19


def test_playback_loops_with_backpressure_and_pause_retains_frame(qtbot) -> None:  # type: ignore[no-untyped-def]
    session, decoder = configured_session(qtbot, frames=20)
    session.window_start, session.window_stop = 4, 8
    session.current_frame = session.displayed_frame = 7
    session.playing = True
    session._play_tick()
    assert session.current_frame == 4 and decoder.frames == [4]
    session._play_tick()
    assert decoder.frames == [4]
    session.displayed_frame = 4
    session._play_tick()
    assert decoder.frames == [4, 5]
    session.pause()
    assert session.current_frame == 5 and not session.playing


def test_frame_navigation_clamps_to_selected_window(qtbot) -> None:  # type: ignore[no-untyped-def]
    session, decoder = configured_session(qtbot, frames=20)
    session.window_start, session.window_stop = 4, 8
    session.current_frame = 6
    session.step(20)
    assert session.current_frame == 7
    session.seek_home()
    assert session.current_frame == 4
    session.seek_end()
    assert session.current_frame == 7
    assert decoder.frames == [7, 4, 7]


def test_timeline_click_preserves_length_and_latest_request_wins(qtbot) -> None:  # type: ignore[no-untyped-def]
    session, decoder = configured_session(qtbot, frames=100)
    session.window_start, session.window_stop = 20, 40
    session.current_frame = 25
    session.timeline_seek(30)
    assert (session.window_start, session.window_stop) == (20, 40)
    session.timeline_seek(80)
    assert (session.window_start, session.window_stop) == (70, 90)
    assert session.current_frame == 80
    session.request_frame(81)
    session.request_frame(82)
    assert decoder.frames[-1] == 82


def test_timeline_drag_defers_decode_until_settled(qtbot) -> None:  # type: ignore[no-untyped-def]
    session, decoder = configured_session(qtbot, frames=100)
    session.window_start, session.window_stop = 20, 40
    session.timeline_scrub(30)
    session.timeline_scrub(80)
    assert decoder.frames == []
    assert session.current_frame == 80
    assert session.scrub_timer.isActive()
    session.settle_timeline_scrub(82)
    assert decoder.frames == [82]
    assert not session.scrub_timer.isActive()


def test_late_decode_results_are_ignored(qtbot) -> None:  # type: ignore[no-untyped-def]
    session, _ = configured_session(qtbot, frames=20)
    session._generation = 4
    session.current_frame = 3
    session.media = type(
        "Media", (), {"metadata": {"width": 2, "height": 2}}
    )()  # type: ignore[assignment]
    ready: list[int] = []
    session.frame_ready.connect(lambda frame, *_: ready.append(frame))
    session._frame_decoded(3, 3, bytes(12), 2, 2)
    session._frame_decoded(4, 2, bytes(12), 2, 2)
    session._frame_decoded(4, 3, bytes(12), 2, 2)
    assert ready == [3]


def test_timeline_maps_full_asset_window_and_cursor(qtbot) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.gui.isolate_timeline import IsolateTimeline
    timeline = IsolateTimeline(); qtbot.addWidget(timeline)
    timeline.resize(1000, 72)
    timeline.set_state(100, 20, 40, 39)
    track = timeline.content_rect()
    assert timeline.boundary_to_x(0) == track.left()
    assert timeline.boundary_to_x(100) == track.right()
    assert timeline.window_rect().left() == timeline.boundary_to_x(20)
    assert timeline.window_rect().right() == timeline.boundary_to_x(40)
    assert timeline.frame_to_x(39) < timeline.window_rect().right()
    assert timeline.x_to_frame(track.right()) == 99


def test_timeline_drag_emits_latest_scrub_position(qtbot) -> None:  # type: ignore[no-untyped-def]
    from PyQt6.QtCore import QPointF, Qt
    from PyQt6.QtGui import QMouseEvent
    from antscihub_sieve.gui.isolate_timeline import IsolateTimeline
    timeline = IsolateTimeline(); qtbot.addWidget(timeline)
    timeline.resize(1000, 72); timeline.set_state(100, 20, 40, 20)
    requested: list[int] = []
    settled: list[int] = []
    timeline.frame_clicked.connect(requested.append)
    timeline.scrub_finished.connect(settled.append)
    y = timeline.content_rect().center().y()
    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress, QPointF(100, y), QPointF(100, y),
        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    timeline.mousePressEvent(press)
    for x in (300, 600, 900):
        move = QMouseEvent(
            QMouseEvent.Type.MouseMove, QPointF(x, y), QPointF(x, y),
            Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        timeline.mouseMoveEvent(move)
    release = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease, QPointF(900, y), QPointF(900, y),
        Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    timeline.mouseReleaseEvent(release)
    assert requested[-1] == timeline.x_to_frame(900)
    assert len(requested) == 4
    assert settled == [timeline.x_to_frame(900)]


def test_player_letterboxes_without_cropping(qtbot) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.gui.isolate_player import IsolatePlayer
    player = IsolatePlayer(); qtbot.addWidget(player)
    player.resize(600, 400)
    player.set_frame(bytes(200 * 100 * 3), 200, 100)
    drawn = player.image_rect()
    assert drawn.width() == 600
    assert drawn.height() == 300
    assert drawn.top() == 50


def test_main_window_shortcuts_dispatch_only_to_active_tab(qtbot, video: Path) -> None:  # type: ignore[no-untyped-def]
    from PyQt6.QtCore import Qt
    from PyQt6.QtTest import QTest
    from antscihub_sieve.gui.main_window import MainWindow
    window = MainWindow(); qtbot.addWidget(window)
    window.show(); window.open_asset(video)
    qtbot.waitUntil(lambda: window.isolate_tab.player.image is not None, timeout=5000)
    window.tabs.setCurrentWidget(window.isolate_tab)
    QTest.keyClick(window, Qt.Key.Key_Space)
    assert window.isolate_tab.session.playing
    QTest.keyClick(window, Qt.Key.Key_Space)
    assert not window.isolate_tab.session.playing
    window.isolate_tab.start_spin.setFocus()
    QTest.keyClick(window.isolate_tab.start_spin, Qt.Key.Key_Space)
    assert not window.isolate_tab.session.playing
    QTest.keyClick(window, Qt.Key.Key_1, Qt.KeyboardModifier.ControlModifier)
    assert window.tabs.currentWidget() is window.replicates_tab
    QTest.keyClick(window, Qt.Key.Key_2, Qt.KeyboardModifier.ControlModifier)
    assert window.tabs.currentWidget() is window.isolate_tab
    window.close()


def test_isolate_layout_has_empty_channels_and_no_processing_controls(qtbot) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.application.active_asset import ActiveAssetController
    from antscihub_sieve.gui.isolate_tab import IsolateTab
    tab = IsolateTab(ActiveAssetController()); qtbot.addWidget(tab)
    tab.resize(900, 600); tab.show()
    assert tab.channels.isVisible()
    assert tab.channels_empty.text() == "No channels added yet."
    visible_text = " ".join(
        label.text() for label in tab.findChildren(type(tab.channels_empty))
    ).casefold()
    for forbidden in (
        "preprocessing", "detection", "tensor", "optical flow", "recipe"
    ):
        assert forbidden not in visible_text
    assert not tab.play_button.isEnabled()
    assert tab.timeline.frame_count == 0
    tab.close()


def test_one_frame_asset_displays_but_cannot_loop(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.application.active_asset import ActiveAssetController
    from antscihub_sieve.gui.isolate_tab import IsolateTab
    one_frame = tmp_path / "one-frame.mkv"
    completed = subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
            "color=size=18x14:rate=1:duration=1",
            "-frames:v", "1", "-c:v", "ffv1", str(one_frame),
        ],
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    controller = ActiveAssetController()
    tab = IsolateTab(controller); qtbot.addWidget(tab); tab.show()
    controller.open_asset(one_frame)
    qtbot.waitUntil(lambda: tab.player.image is not None, timeout=5000)
    assert tab.session.frame_count == 1
    assert not tab.play_button.isEnabled()
    assert "at least two" in tab.status_label.text()
    tab.close()


def test_probe_failure_keeps_stable_error_and_no_media_session(qtbot, monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.application.active_asset import ActiveAsset
    from antscihub_sieve.errors import SieveError
    import antscihub_sieve.gui.isolate_session as isolate_session
    def fail(_path):  # type: ignore[no-untyped-def]
        raise SieveError("MEDIA_PROBE_FAILED", "Video probing failed")
    monkeypatch.setattr(isolate_session, "MediaSession", fail)
    session = isolate_session.IsolateSession()
    asset = ActiveAsset(
        asset_id="a", sidecar_path=tmp_path / "a.asset.json",
        video_path=tmp_path / "a.mkv", label="a", kind="video",
        width=1, height=1, fps_num=1, fps_den=1,
        duration_seconds=1.0, parent=None,
    )
    session.open_asset(asset)
    assert session.media is None and session.decoder is None
    assert session.error_text == "MEDIA_PROBE_FAILED: Video probing failed"
    assert not session.play_timer.isActive()


def test_closing_main_window_stops_isolate_media_and_timer(qtbot, video: Path) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.gui.main_window import MainWindow
    window = MainWindow(); qtbot.addWidget(window); window.show()
    window.open_asset(video)
    qtbot.waitUntil(lambda: window.isolate_tab.player.image is not None, timeout=5000)
    isolate = window.isolate_tab
    isolate.session.toggle_play()
    assert isolate.session.play_timer.isActive()
    window.close()
    assert not isolate.session.play_timer.isActive()
    assert isolate.session.media is None
    assert isolate.session.decoder is None
