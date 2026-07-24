from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from typing import Any

from antscihub_sieve.media.benchmark import (
    environment_metadata,
    latency_summary,
)


def asset_metadata(path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "codec": metadata.get("codec"),
        "pixel_format": metadata.get("pixel_format"),
        "width": metadata.get("width"),
        "height": metadata.get("height"),
        "fps_num": metadata.get("fps_num"),
        "fps_den": metadata.get("fps_den"),
        "duration_seconds": metadata.get("duration_seconds"),
    }


def write_result(result: dict[str, Any], output: Path | None) -> None:
    import json

    rendered = json.dumps(result, indent=2, sort_keys=True)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark SIEVE decode-to-Qt-display stages."
    )
    parser.add_argument("asset", type=Path)
    parser.add_argument("--frames", type=int, default=12)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--channel-overlays",
        action="store_true",
        help="Also benchmark grid and representative selected-channel overlays.",
    )
    parser.add_argument(
        "--change-overlay",
        action="store_true",
        help="Use the adaptive TURBO Change-energy mapping in the overlay matrix.",
    )
    args = parser.parse_args()

    from PyQt6.QtWidgets import QApplication

    from antscihub_sieve.gui.isolate_player import IsolatePlayer
    from antscihub_sieve.gui.isolate_session import ISOLATE_DISPLAY_MAX_WIDTH
    from antscihub_sieve.media.session import MediaSession

    application = QApplication.instance() or QApplication([])
    player = IsolatePlayer()
    player.resize(args.width, args.height)
    player.show()
    application.processEvents()

    path = args.asset.resolve()
    session = MediaSession(path)
    decode_ms: list[float] = []
    install_ms: list[float] = []
    paint_ms: list[float] = []
    end_to_end_ms: list[float] = []
    unchanged_repaint_ms: list[float] = []
    overlay_measurements: dict[str, Any] = {}
    try:
        frame_count = min(args.frames, session.frame_count)
        display_width, display_height = session.scaled_dimensions(
            ISOLATE_DISPLAY_MAX_WIDTH
        )
        for frame in range(frame_count):
            started = time.perf_counter_ns()
            raw = session.read_frame_rgb(
                frame, max_width=ISOLATE_DISPLAY_MAX_WIDTH
            )
            decoded = time.perf_counter_ns()
            player.set_frame(
                raw,
                display_width,
                display_height,
                frame,
            )
            installed = time.perf_counter_ns()
            player.repaint()
            application.processEvents()
            painted = time.perf_counter_ns()
            decode_ms.append((decoded - started) / 1_000_000)
            install_ms.append((installed - decoded) / 1_000_000)
            paint_ms.append((painted - installed) / 1_000_000)
            end_to_end_ms.append((painted - started) / 1_000_000)

        for _ in range(max(5, frame_count)):
            started = time.perf_counter_ns()
            player.repaint()
            application.processEvents()
            unchanged_repaint_ms.append(
                (time.perf_counter_ns() - started) / 1_000_000
            )
        if args.channel_overlays:
            import numpy as np

            from antscihub_sieve.application.working_grid import (
                resolve_working_grid,
            )
            from antscihub_sieve.gui.intensity_panel import (
                CHANGE_OFF_PRESENTATION_ID,
                OFF_PRESENTATION_ID,
            )
            from antscihub_sieve.gui.isolate_player import ChannelOverlay

            grid = resolve_working_grid(
                int(session.metadata["width"]), int(session.metadata["height"])
            )
            values = np.linspace(
                0.0,
                1.0,
                grid.rows * grid.columns,
                dtype=np.float32,
            ).reshape(grid.rows, grid.columns)
            values.setflags(write=False)
            mapping = (
                CHANGE_OFF_PRESENTATION_ID
                if args.change_overlay
                else OFF_PRESENTATION_ID
            )
            overlay = ChannelOverlay(
                publication_token=1,
                absolute_frame=frame_count - 1,
                grid=grid,
                values=values,
                presentation_mapping_id=mapping,
                channel_label=(
                    "Change energy" if args.change_overlay else "Intensity"
                ),
                scientific_units=(
                    "post-decoder intensity squared"
                    if args.change_overlay
                    else "normalized RGB-code intensity fraction"
                ),
                detail="representative benchmark field",
                display_scale=(
                    float(np.percentile(values, 99))
                    if args.change_overlay
                    else 1.0
                ),
            )
            for name, show_overlay, show_grid in (
                ("video_only", False, False),
                ("video_plus_grid", False, True),
                ("video_plus_channel_overlay", True, False),
                ("video_plus_channel_overlay_plus_grid", True, True),
            ):
                player.set_working_grid(grid, visible=show_grid)
                player.set_channel_overlay(
                    overlay if show_overlay else None,
                    visible=show_overlay,
                )
                preparation_ms = 0.0
                if show_overlay:
                    prepared = time.perf_counter_ns()
                    player._channel_overlay_image(player.image_rect())
                    preparation_ms = (
                        time.perf_counter_ns() - prepared
                    ) / 1_000_000
                samples: list[float] = []
                for _ in range(max(8, frame_count)):
                    started = time.perf_counter_ns()
                    player.repaint()
                    application.processEvents()
                    samples.append(
                        (time.perf_counter_ns() - started) / 1_000_000
                    )
                overlay_measurements[name] = {
                    "overlay_preparation_ms": preparation_ms,
                    "paint": latency_summary(samples),
                }
    finally:
        metadata: dict[str, Any] = session.metadata
        session.close()
        player.close()
        application.processEvents()

    result = {
        "schema_version": 1,
        "mode": "viewer",
        "environment": {
            **environment_metadata(),
            "qt_qpa_platform_env": os.environ.get("QT_QPA_PLATFORM"),
            "qt_platform_plugin": application.platformName(),
            "device_pixel_ratio": player.devicePixelRatioF(),
        },
        "asset": asset_metadata(path, metadata),
        "configuration": {
            "frames": frame_count,
            "display_decode_max_width": ISOLATE_DISPLAY_MAX_WIDTH,
            "decoded_frame_size": [display_width, display_height],
            "window_size": [args.width, args.height],
            "window_visible": True,
            "window_obscured_or_minimized": False,
            "synchronous_repaint": True,
            "channel_overlay_matrix": args.channel_overlays,
            "change_overlay": args.change_overlay,
        },
        "measurements": {
            "sequential_decode": latency_summary(decode_ms),
            "steady_state_sequential_decode": latency_summary(decode_ms[1:]),
            "qt_image_install": latency_summary(install_ms),
            "steady_state_qt_image_install": latency_summary(install_ms[1:]),
            "paint": latency_summary(paint_ms),
            "steady_state_paint": latency_summary(paint_ms[1:]),
            "decode_to_paint": latency_summary(end_to_end_ms),
            "steady_state_decode_to_paint": latency_summary(
                end_to_end_ms[1:]
            ),
            "unchanged_frame_repaint": latency_summary(unchanged_repaint_ms),
            "overlay_matrix": overlay_measurements,
        },
        "counts": {
            "requested": frame_count,
            "decoded": frame_count,
            "delivered": frame_count,
            "painted": frame_count + len(unchanged_repaint_ms),
            "failed": 0,
        },
    }
    write_result(result, args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
