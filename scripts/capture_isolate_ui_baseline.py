from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Callable


def wait_until(
    application,
    predicate: Callable[[], bool],
    *,
    timeout_seconds: float = 20.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while not predicate():
        application.processEvents()
        if time.monotonic() >= deadline:
            raise TimeoutError("Timed out waiting for baseline GUI state")
        time.sleep(0.01)


def widget_inventory(root) -> list[dict[str, object]]:
    from PyQt6.QtWidgets import QAbstractButton, QSplitter, QWidget

    records: list[dict[str, object]] = []
    for widget in [root, *root.findChildren(QWidget)]:
        text_getter = getattr(widget, "text", None)
        geometry = widget.geometry()
        record: dict[str, object] = {
            "class": type(widget).__name__,
            "object_name": widget.objectName(),
            "visible": widget.isVisible(),
            "enabled": widget.isEnabled(),
            "minimum_size": [
                widget.minimumWidth(),
                widget.minimumHeight(),
            ],
            "geometry": [
                geometry.x(),
                geometry.y(),
                geometry.width(),
                geometry.height(),
            ],
        }
        if callable(text_getter):
            record["text"] = text_getter()
        if isinstance(widget, QAbstractButton):
            record["checkable"] = widget.isCheckable()
            record["checked"] = widget.isChecked()
        if isinstance(widget, QSplitter):
            record["splitter_sizes"] = widget.sizes()
        records.append(record)
    return records


def capture_sieve(args, application) -> tuple[object, Callable[[], None]]:
    from antscihub_sieve.application.active_asset import ActiveAssetController
    from antscihub_sieve.gui.isolate_tab import IsolateTab

    controller = ActiveAssetController()
    surface = IsolateTab(controller)
    surface.resize(args.width, args.height)
    surface.show()
    application.processEvents()
    if args.state == "computed":
        controller.open_asset(args.video)
        wait_until(application, lambda: surface.session.displayed_frame is not None)
        surface.session.set_window_length(
            min(64, surface.session.frame_count)
        )
        surface.channel_combo.setCurrentIndex(1)
        surface.compute_intensity_button.click()
        wait_until(
            application,
            lambda: surface._intensity_worker is None,
            timeout_seconds=60.0,
        )
        if surface._selected_result is None:
            raise RuntimeError("SIEVE Change-energy baseline did not complete")
        surface.session.pause()
        surface.session.request_frame(
            min(surface.session.window_start + 3, surface.session.window_stop - 1)
        )
        wait_until(
            application,
            lambda: (
                surface.player.displayed_frame
                == surface.session.current_frame
            ),
        )
    return surface, surface.shutdown


def capture_oracle(args, application) -> tuple[object, Callable[[], None]]:
    import numpy as np

    sys.path.insert(0, str(args.oracle_root))
    from core.channel_source import ChannelData
    from gui.explorers.live_scalogram_surface import LiveScalogramSurface

    replicates = [
        {"id": 0, "label": "all", "frac": (0.0, 0.0, 1.0, 1.0)}
    ]
    surface = LiveScalogramSurface(str(args.video), replicates)
    surface.resize(args.width, args.height)
    surface.show()
    application.processEvents()
    if args.state == "computed":
        frame_count = min(64, surface.frame_count)
        rows = columns = 4
        rng = np.random.default_rng(20260723)
        channels = {
            name: rng.random(
                (frame_count, rows, columns),
                dtype=np.float32,
            )
            + np.float32(0.1)
            for name in (
                "change",
                "appearance",
                "tensor_speed",
                "intensity",
            )
        }
        meta = {
            "video_path": str(args.video),
            "backend": "chunk-0-presentation-fixture",
            "fps": float(surface.fps),
            "grid": [rows, columns],
            "block_size": 64,
            "n_frames": frame_count,
            "src_width": int(surface._dims[0]),
            "src_height": int(surface._dims[1]),
            "work_width": columns * 64,
            "work_height": rows * 64,
            "replicate_tiles": [
                {
                    "id": 0,
                    "label": "all",
                    "atlas_bbox": [0, 0, rows, columns],
                    "frac": [0.0, 0.0, 1.0, 1.0],
                }
            ],
        }
        data = ChannelData(meta=meta, channels=channels)
        surface._put_on_screen(data, live=False)
        wait_until(application, lambda: surface._explorer is not None)
        application.processEvents()
        time.sleep(0.25)
        application.processEvents()

    def shutdown() -> None:
        surface.close()
        surface.deleteLater()
        application.processEvents()

    return surface, shutdown


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture matched Chunk-0 oracle and SIEVE UI baselines."
    )
    parser.add_argument("surface", choices=("oracle", "sieve"))
    parser.add_argument("state", choices=("empty", "computed"))
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inventory-out", type=Path)
    parser.add_argument(
        "--oracle-root",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "antscihub-optical-flow-detector",
    )
    args = parser.parse_args()

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
    from PyQt6.QtCore import QRect
    from PyQt6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication([])
    capture = capture_oracle if args.surface == "oracle" else capture_sieve
    surface, shutdown = capture(args, application)
    try:
        application.processEvents()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        capture_rect = QRect(0, 0, args.width, args.height)
        if not surface.grab(capture_rect).save(str(args.output)):
            raise RuntimeError(f"Could not save screenshot: {args.output}")
        if args.inventory_out is not None:
            args.inventory_out.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "surface": args.surface,
                "state": args.state,
                "window_size": [args.width, args.height],
                "actual_surface_size": [surface.width(), surface.height()],
                "captured_size": [args.width, args.height],
                "qt_platform": application.platformName(),
                "widgets": widget_inventory(surface),
            }
            args.inventory_out.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    finally:
        shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
