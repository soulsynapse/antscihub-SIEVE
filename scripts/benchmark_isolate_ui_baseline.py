from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from pathlib import Path
from typing import Callable


def wait_until(
    application,
    predicate: Callable[[], bool],
    *,
    timeout_seconds: float = 30.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while not predicate():
        application.processEvents()
        if time.monotonic() >= deadline:
            raise TimeoutError("Timed out waiting for Isolate baseline state")
        time.sleep(0.001)


def summary(samples: list[float]) -> dict[str, float | int]:
    ordered = sorted(samples)
    return {
        "count": len(samples),
        "minimum_ms": ordered[0],
        "median_ms": statistics.median(ordered),
        "p95_ms": ordered[min(len(ordered) - 1, round(0.95 * len(ordered)))],
        "maximum_ms": ordered[-1],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark the current visible SIEVE Isolate panel."
    )
    parser.add_argument("video", type=Path)
    parser.add_argument("--samples", type=int, default=12)
    parser.add_argument("--width", type=int, default=1200)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args()

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
    from PyQt6.QtWidgets import QApplication

    from antscihub_sieve.application.active_asset import ActiveAssetController
    from antscihub_sieve.gui.isolate_tab import IsolateTab

    application = QApplication.instance() or QApplication([])
    controller = ActiveAssetController()
    tab = IsolateTab(controller)
    tab.resize(args.width, args.height)
    tab.show()
    application.processEvents()
    controller.open_asset(args.video)
    wait_until(application, lambda: tab.session.displayed_frame is not None)
    tab.session.set_window_length(min(64, tab.session.frame_count))
    tab.channel_combo.setCurrentIndex(1)
    tab.compute_intensity_button.click()
    wait_until(
        application,
        lambda: tab._intensity_worker is None,
        timeout_seconds=60.0,
    )
    if tab._selected_result is None:
        raise RuntimeError("Change-energy baseline did not complete")
    tab.session.pause()

    unchanged_paint_ms: list[float] = []
    seek_to_paint_ms: list[float] = []
    playback_tick_to_paint_ms: list[float] = []
    start = tab.session.window_start
    length = tab.session.window_length
    targets = [
        start + 1 + (index * max(1, length - 2) // max(1, args.samples - 1))
        for index in range(args.samples)
    ]
    try:
        for _ in range(args.samples):
            began = time.perf_counter_ns()
            tab.grab()
            application.processEvents()
            unchanged_paint_ms.append(
                (time.perf_counter_ns() - began) / 1_000_000
            )

        for target in targets:
            began = time.perf_counter_ns()
            tab.session.timeline_seek(target)
            wait_until(
                application,
                lambda target=target: tab.session.displayed_frame == target,
            )
            tab.grab()
            application.processEvents()
            seek_to_paint_ms.append(
                (time.perf_counter_ns() - began) / 1_000_000
            )

        tab.session.request_frame(start)
        wait_until(application, lambda: tab.session.displayed_frame == start)
        tab.session.toggle_play()
        tab.session.play_timer.stop()
        for _ in range(args.samples):
            began = time.perf_counter_ns()
            previous = tab.session.displayed_frame
            tab.session._play_tick()
            wait_until(
                application,
                lambda previous=previous: (
                    tab.session.displayed_frame != previous
                ),
            )
            tab.grab()
            application.processEvents()
            playback_tick_to_paint_ms.append(
                (time.perf_counter_ns() - began) / 1_000_000
            )
        tab.session.pause()

        payload = {
            "schema_version": 1,
            "mode": "chunk-0-isolate-visible-panel-baseline",
            "environment": {
                "qt_qpa_platform_env": os.environ.get("QT_QPA_PLATFORM"),
                "qt_platform_plugin": application.platformName(),
                "device_pixel_ratio": tab.devicePixelRatioF(),
            },
            "asset": str(args.video.resolve()),
            "configuration": {
                "window_size": [args.width, args.height],
                "samples": args.samples,
                "channel": "change_energy",
                "working_window_frames": length,
                "full_widget_grab": True,
            },
            "measurements": {
                "unchanged_full_panel_paint": summary(unchanged_paint_ms),
                "timeline_seek_decode_to_full_panel_paint": summary(
                    seek_to_paint_ms
                ),
                "playback_tick_decode_to_full_panel_paint": summary(
                    playback_tick_to_paint_ms
                ),
            },
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
    finally:
        tab.shutdown()
        tab.close()
        application.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
