from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from typing import Callable

from antscihub_sieve.media.benchmark import (
    environment_metadata,
    latency_summary,
)


def write_result(result: dict, output: Path | None) -> None:  # type: ignore[type-arg]
    import json

    rendered = json.dumps(result, indent=2, sort_keys=True)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


def wait_until(
    application, predicate: Callable[[], bool], timeout_seconds: float = 10.0
) -> float:
    started = time.perf_counter_ns()
    deadline = time.monotonic() + timeout_seconds
    while not predicate():
        application.processEvents()
        if time.monotonic() >= deadline:
            raise TimeoutError("Timed out waiting for media interaction")
        time.sleep(0.001)
    application.processEvents()
    return (time.perf_counter_ns() - started) / 1_000_000


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark Isolate scrub and asset-switch behavior."
    )
    parser.add_argument("asset", type=Path)
    parser.add_argument("switch_asset", type=Path)
    parser.add_argument("--scrub-requests", type=int, default=100)
    parser.add_argument("--scrub-seconds", type=float, default=1.0)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    from PyQt6.QtWidgets import QApplication

    from antscihub_sieve.application.active_asset import ActiveAsset
    from antscihub_sieve.gui.isolate_session import IsolateSession
    from antscihub_sieve.media.probe import run_ffprobe

    def active_asset(path: Path) -> ActiveAsset:
        path = path.resolve()
        metadata = run_ffprobe(path)
        return ActiveAsset(
            asset_id=str(path),
            sidecar_path=path.with_suffix(".asset.json"),
            video_path=path,
            label=path.stem,
            kind="video",
            width=int(metadata["width"]),
            height=int(metadata["height"]),
            fps_num=int(metadata["fps_num"]),
            fps_den=int(metadata["fps_den"]),
            duration_seconds=float(metadata["duration_seconds"]),
            parent=None,
        )

    application = QApplication.instance() or QApplication([])
    session = IsolateSession()
    frames_ready: list[tuple[int, int]] = []
    session.frame_ready.connect(
        lambda frame, _raw, width, height: frames_ready.append(
            (frame, width * height)
        )
    )

    source = active_asset(args.asset)
    switched = active_asset(args.switch_asset)
    opened = time.perf_counter_ns()
    session.open_asset(source)
    open_call_ms = (time.perf_counter_ns() - opened) / 1_000_000
    open_to_first_frame_ms = open_call_ms + wait_until(
        application, lambda: session.displayed_frame == 0
    )

    frames_ready.clear()
    positions = [
        round(
            (source.duration_seconds * source.fps_num / source.fps_den - 1)
            * index
            / max(1, args.scrub_requests - 1)
        )
        for index in range(args.scrub_requests)
    ]
    interval = args.scrub_seconds / max(1, args.scrub_requests - 1)
    scrub_started = time.perf_counter_ns()
    for position in positions:
        session.timeline_scrub(position)
        application.processEvents()
        if interval:
            time.sleep(interval)
    session.settle_timeline_scrub(positions[-1])
    released = time.perf_counter_ns()
    final_target = session.current_frame
    final_release_latency_ms = wait_until(
        application, lambda: session.displayed_frame == final_target
    )
    final_scrub_frame_displayed = session.displayed_frame == final_target
    total_scrub_ms = (time.perf_counter_ns() - scrub_started) / 1_000_000
    delivered_during_drag = len(frames_ready)

    frames_ready.clear()
    session.timeline_seek(max(0, session.frame_count // 2))
    switch_started = time.perf_counter_ns()
    session.open_asset(switched)
    switch_call_ms = (time.perf_counter_ns() - switch_started) / 1_000_000
    switch_to_first_frame_ms = switch_call_ms + wait_until(
        application,
        lambda: session.asset == switched and session.displayed_frame == 0,
    )
    switch_frame_area = frames_ready[-1][1] if frames_ready else None
    expected_switch_dimensions = session.media.scaled_dimensions(1280)

    close_started = time.perf_counter_ns()
    session.close()
    close_ms = (time.perf_counter_ns() - close_started) / 1_000_000
    clean_state = (
        session.decoder is None
        and session.media is None
        and not session.play_timer.isActive()
    )

    result = {
        "schema_version": 1,
        "mode": "interactions",
        "environment": {
            **environment_metadata(),
            "qt_qpa_platform_env": os.environ.get("QT_QPA_PLATFORM"),
            "qt_platform_plugin": application.platformName(),
        },
        "assets": {
            "initial": str(source.video_path),
            "switched": str(switched.video_path),
        },
        "configuration": {
            "scrub_requests": args.scrub_requests,
            "scrub_seconds_target": args.scrub_seconds,
        },
        "measurements": {
            "open_call_plus_first_frame": latency_summary(
                [open_to_first_frame_ms]
            ),
            "open_call_return": latency_summary([open_call_ms]),
            "final_scrub_release_to_frame": latency_summary(
                [final_release_latency_ms]
            ),
            "total_scrub": latency_summary([total_scrub_ms]),
            "asset_switch_call_return": latency_summary([switch_call_ms]),
            "asset_switch_to_first_frame": latency_summary(
                [switch_to_first_frame_ms]
            ),
            "close": latency_summary([close_ms]),
        },
        "counts": {
            "scrub_requests": len(positions),
            "frames_delivered_during_or_after_scrub": delivered_during_drag,
        },
        "correctness": {
            "final_scrub_frame_displayed": final_scrub_frame_displayed,
            "switch_frame_area": switch_frame_area,
            "expected_switch_frame_area": (
                expected_switch_dimensions[0] * expected_switch_dimensions[1]
            ),
            "clean_state_after_close": clean_state,
        },
    }
    write_result(result, args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
