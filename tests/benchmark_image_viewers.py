"""Compare candidate SIEVE image-viewer backends under one raster workload.

This is an architectural experiment, not a pytest test.  The controller starts
each backend in a fresh process because Qt applications and OpenGL contexts are
not reliably reusable after a viewer has been torn down.

Examples
--------
Fast headless smoke test (napari is expected to fail on Windows/Qt offscreen)::

    python tests/benchmark_image_viewers.py --offscreen --frames 12 \
        --warmup-frames 3 --width 640 --height 360

Real renderer comparison on the active Windows display/GPU::

    python tests/benchmark_image_viewers.py --frames 180 --warmup-frames 30 \
        --width 1920 --height 1080 --fps 30
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import traceback
from typing import Any, Callable, Protocol


BACKENDS = ("qt-native", "pyqtgraph", "napari")


class ViewerBackend(Protocol):
    widget: Any
    presentation_boundary: str

    def publish(self, frame_id: int, rgb: Any, composite: Any, current: Any) -> None:
        """Publish a frame and two same-generation RGBA overlays."""

    def close(self) -> None:
        """Release viewer resources."""


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _make_fixture_ring(width: int, height: int, ring_size: int) -> list[tuple[Any, Any, Any]]:
    import numpy as np

    x = np.arange(width, dtype=np.uint16)[None, :]
    y = np.arange(height, dtype=np.uint16)[:, None]
    fixtures: list[tuple[Any, Any, Any]] = []

    for slot in range(ring_size):
        rgb = np.empty((height, width, 3), dtype=np.uint8)
        rgb[..., 0] = (x + slot * 37) & 255
        rgb[..., 1] = (y + slot * 61) & 255
        rgb[..., 2] = ((x // 2 + y // 2) + slot * 23) & 255

        composite = np.zeros((height, width, 4), dtype=np.uint8)
        stripe = ((x + y + slot * 19) % 96) < 24
        composite[..., 1] = np.where(stripe, 255, 0)
        composite[..., 3] = np.where(stripe, 72, 0)

        current = np.zeros((height, width, 4), dtype=np.uint8)
        box_width = max(16, width // 5)
        box_height = max(16, height // 5)
        left = (slot * max(1, width // ring_size)) % max(1, width - box_width)
        top = (slot * max(1, height // (ring_size + 1))) % max(1, height - box_height)
        current[top : top + box_height, left : left + box_width, 0] = 255
        current[top : top + box_height, left : left + box_width, 2] = 210
        current[top : top + box_height, left : left + box_width, 3] = 110
        fixtures.append((rgb, composite, current))

    return fixtures


def _qimage(array: Any, image_format: Any) -> Any:
    from qtpy.QtGui import QImage

    height, width = array.shape[:2]
    return QImage(
        array.data,
        width,
        height,
        int(array.strides[0]),
        image_format,
    )


class QtNativeBackend:
    """QGraphicsView baseline with Qt-owned pan, zoom, and layered pixmaps."""

    presentation_boundary = "QGraphicsView.drawForeground after scene composition"

    def __init__(
        self,
        first: tuple[Any, Any, Any],
        presented: Callable[[int], None],
    ) -> None:
        from qtpy.QtCore import Qt
        from qtpy.QtGui import QImage, QPainter, QPixmap
        from qtpy.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView

        owner = self

        class MeasuredGraphicsView(QGraphicsView):
            def drawForeground(self, painter: QPainter, rect: Any) -> None:  # noqa: N802
                super().drawForeground(painter, rect)
                presented(owner._frame_id)

            def wheelEvent(self, event: Any) -> None:  # noqa: N802
                factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
                self.scale(factor, factor)

        self._frame_id = -1
        self._arrays = first
        self._scene = QGraphicsScene()
        self.widget = MeasuredGraphicsView(self._scene)
        self.widget.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        self.widget.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.widget.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._items = [QGraphicsPixmapItem() for _ in range(3)]
        for item in self._items:
            self._scene.addItem(item)
        self._formats = (
            QImage.Format.Format_RGB888,
            QImage.Format.Format_RGBA8888,
            QImage.Format.Format_RGBA8888,
        )
        self.publish(0, *first)
        height, width = first[0].shape[:2]
        self._scene.setSceneRect(0, 0, width, height)
        self.widget.fitInView(
            self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
        )

    def publish(self, frame_id: int, rgb: Any, composite: Any, current: Any) -> None:
        from qtpy.QtGui import QPixmap

        self._frame_id = frame_id
        self._arrays = (rgb, composite, current)
        for item, array, image_format in zip(
            self._items, self._arrays, self._formats, strict=True
        ):
            item.setPixmap(QPixmap.fromImage(_qimage(array, image_format)))
        self.widget.viewport().update()

    def close(self) -> None:
        self._scene.clear()
        self.widget.close()


class PyqtgraphBackend:
    """pyqtgraph ImageItem stack inside a ViewBox."""

    presentation_boundary = "top pyqtgraph ImageItem.paint after composition"

    def __init__(
        self,
        first: tuple[Any, Any, Any],
        presented: Callable[[int], None],
    ) -> None:
        import pyqtgraph as pg

        owner = self

        class MeasuredImageItem(pg.ImageItem):
            def paint(self, painter: Any, *args: Any) -> None:
                super().paint(painter, *args)
                presented(owner._frame_id)

        self._frame_id = -1
        self.widget = pg.GraphicsLayoutWidget()
        self._view = self.widget.addViewBox(lockAspect=True, invertY=True)
        self._view.setMouseMode(self._view.PanMode)
        self._raw = pg.ImageItem(axisOrder="row-major")
        self._composite = pg.ImageItem(axisOrder="row-major")
        self._current = MeasuredImageItem(axisOrder="row-major")
        for item in (self._raw, self._composite, self._current):
            self._view.addItem(item)
        self.publish(0, *first)
        self._view.autoRange()

    def publish(self, frame_id: int, rgb: Any, composite: Any, current: Any) -> None:
        self._frame_id = frame_id
        self._raw.setImage(rgb, autoLevels=False)
        self._composite.setImage(composite, autoLevels=False)
        self._current.setImage(current, autoLevels=False)

    def close(self) -> None:
        self.widget.close()


class NapariBackend:
    """Public embedded napari ViewerModel + QtViewer."""

    presentation_boundary = "VisPy canvas draw event (not display scan-out)"

    def __init__(
        self,
        first: tuple[Any, Any, Any],
        presented: Callable[[int], None],
    ) -> None:
        from napari.components import ViewerModel
        from napari.qt import QtViewer

        self._frame_id = -1
        self._model = ViewerModel(title="SIEVE viewer ADR benchmark", ndisplay=2)
        self.widget = QtViewer(self._model, show_welcome_screen=False)
        self.widget.canvas.events.draw.connect(
            lambda event: presented(self._frame_id)
        )
        rgb, composite, current = first
        self._raw = self._model.add_image(
            rgb,
            rgb=True,
            name="raw",
            blending="opaque",
        )
        self._composite = self._model.add_image(
            composite,
            rgb=True,
            name="composite",
            blending="translucent",
        )
        self._current = self._model.add_image(
            current,
            rgb=True,
            name="current",
            blending="translucent",
        )
        self._model.reset_view()

    def publish(self, frame_id: int, rgb: Any, composite: Any, current: Any) -> None:
        self._frame_id = frame_id
        self._raw.data = rgb
        self._composite.data = composite
        self._current.data = current

    def close(self) -> None:
        self._model.layers.clear()
        self.widget.close()


def _create_backend(
    name: str,
    first: tuple[Any, Any, Any],
    presented: Callable[[int], None],
) -> ViewerBackend:
    if name == "qt-native":
        return QtNativeBackend(first, presented)
    if name == "pyqtgraph":
        return PyqtgraphBackend(first, presented)
    if name == "napari":
        return NapariBackend(first, presented)
    raise ValueError(f"Unknown backend: {name}")


class BenchmarkRunner:
    def __init__(
        self,
        *,
        app: Any,
        backend_name: str,
        backend: ViewerBackend,
        fixtures: list[tuple[Any, Any, Any]],
        frames: int,
        warmup_frames: int,
        fps: float,
        screenshot: Path,
        result: dict[str, Any],
    ) -> None:
        import psutil
        from qtpy.QtCore import QTimer, Qt

        self.app = app
        self.backend_name = backend_name
        self.backend = backend
        self.fixtures = fixtures
        self.frames = frames
        self.warmup_frames = warmup_frames
        self.total_frames = frames + warmup_frames
        self.fps = fps
        self.screenshot = screenshot
        self.result = result
        self._next_id = 0
        self._publish_ns: dict[int, int] = {}
        self._presented: set[int] = set()
        self._latency_ms: list[float] = []
        self._tick_ns: list[int] = []
        self._presentation_ns: list[int] = []
        self._process = psutil.Process()
        self._rss_peak = self._process.memory_info().rss
        self._cpu_start: Any | None = None
        self._cpu_end: Any | None = None
        self._measure_start_ns: int | None = None
        self._measure_end_ns: int | None = None
        self._finished = False

        self._timer = QTimer()
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(max(1, round(1000 / fps)))
        self._timer.timeout.connect(self._publish_next)

        self._rss_timer = QTimer()
        self._rss_timer.setInterval(20)
        self._rss_timer.timeout.connect(self._sample_rss)

    def start(self) -> None:
        from qtpy.QtCore import QTimer

        self.backend.widget.show()
        self.app.processEvents()
        self._rss_timer.start()
        QTimer.singleShot(100, self._timer.start)

    def presented(self, frame_id: int) -> None:
        if frame_id < self.warmup_frames or frame_id in self._presented:
            return
        published = self._publish_ns.get(frame_id)
        if published is None:
            return
        now = time.perf_counter_ns()
        self._presented.add(frame_id)
        self._latency_ms.append((now - published) / 1_000_000)
        self._presentation_ns.append(now)
        self._measure_end_ns = now
        if frame_id == self.total_frames - 1:
            self._cpu_end = self._process.cpu_times()

    def _sample_rss(self) -> None:
        self._rss_peak = max(self._rss_peak, self._process.memory_info().rss)

    def _publish_next(self) -> None:
        from qtpy.QtCore import QTimer

        if self._next_id >= self.total_frames:
            self._timer.stop()
            QTimer.singleShot(1000, self.finish)
            return

        frame_id = self._next_id
        now = time.perf_counter_ns()
        self._tick_ns.append(now)
        if frame_id == self.warmup_frames:
            self._measure_start_ns = now
            self._cpu_start = self._process.cpu_times()
        if frame_id >= self.warmup_frames:
            self._publish_ns[frame_id] = now

        fixture = self.fixtures[frame_id % len(self.fixtures)]
        self.backend.publish(frame_id, *fixture)
        self._next_id += 1
        if self._next_id >= self.total_frames:
            self._timer.stop()
            QTimer.singleShot(1000, self.finish)

    def finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        self._timer.stop()
        self._rss_timer.stop()
        self._sample_rss()

        self.screenshot.parent.mkdir(parents=True, exist_ok=True)
        screenshot_saved = self.backend.widget.grab().save(str(self.screenshot))

        cpu_start = self._cpu_start or self._process.cpu_times()
        cpu_end = self._cpu_end or self._process.cpu_times()
        end_ns = self._measure_end_ns or time.perf_counter_ns()
        start_ns = self._measure_start_ns or end_ns
        measured_wall_s = max((end_ns - start_ns) / 1_000_000_000, 1e-9)
        cpu_s = (
            cpu_end.user
            + cpu_end.system
            - cpu_start.user
            - cpu_start.system
        )
        scheduled_duration_s = self.frames / self.fps
        if len(self._presentation_ns) >= 2:
            presentation_span_s = (
                self._presentation_ns[-1] - self._presentation_ns[0]
            ) / 1_000_000_000
            presentation_span_fps = (
                (len(self._presentation_ns) - 1) / presentation_span_s
                if presentation_span_s > 0
                else None
            )
        else:
            presentation_span_fps = None
        measured_ids = set(range(self.warmup_frames, self.total_frames))
        dropped = len(measured_ids - self._presented)
        deadline_ms = 1000 / self.fps
        tick_intervals_ms = [
            (right - left) / 1_000_000
            for left, right in zip(self._tick_ns, self._tick_ns[1:])
        ][self.warmup_frames :]

        self.result.update(
            {
                "status": "ok",
                "presentation_boundary": self.backend.presentation_boundary,
                "presented_frames": len(self._presented),
                "dropped_frames": dropped,
                "drop_rate": dropped / self.frames,
                "latency_ms": {
                    "p50": _percentile(self._latency_ms, 0.50),
                    "p95": _percentile(self._latency_ms, 0.95),
                    "p99": _percentile(self._latency_ms, 0.99),
                    "mean": statistics.fmean(self._latency_ms)
                    if self._latency_ms
                    else None,
                    "max": max(self._latency_ms) if self._latency_ms else None,
                },
                "deadline_ms": deadline_ms,
                "deadline_miss_rate": (
                    sum(value > deadline_ms for value in self._latency_ms)
                    / len(self._latency_ms)
                    if self._latency_ms
                    else None
                ),
                "timer_interval_ms": {
                    "p50": _percentile(tick_intervals_ms, 0.50),
                    "p95": _percentile(tick_intervals_ms, 0.95),
                    "max": max(tick_intervals_ms) if tick_intervals_ms else None,
                },
                "measured_wall_s": measured_wall_s,
                "scheduled_duration_s": scheduled_duration_s,
                "effective_presented_fps": len(self._presented)
                / scheduled_duration_s,
                "presentation_span_fps": presentation_span_fps,
                "cpu_s": cpu_s,
                "cpu_percent_of_one_core": 100 * cpu_s / measured_wall_s,
                "rss_end_mb": self._process.memory_info().rss / (1024**2),
                "rss_peak_mb": self._rss_peak / (1024**2),
                "screenshot": str(self.screenshot),
                "screenshot_saved": bool(screenshot_saved),
            }
        )
        self.backend.close()
        self.app.quit()


def _worker(args: argparse.Namespace) -> int:
    worker_started_ns = time.perf_counter_ns()
    result_path = Path(args.result)
    result: dict[str, Any] = {
        "backend": args.worker,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "qt_api": os.environ.get("QT_API"),
        "qt_qpa_platform": os.environ.get("QT_QPA_PLATFORM"),
        "config": {
            "width": args.width,
            "height": args.height,
            "fps": args.fps,
            "frames": args.frames,
            "warmup_frames": args.warmup_frames,
            "ring_size": args.ring_size,
            "layers": ["rgb", "composite_rgba", "current_rgba"],
        },
        "versions": {
            name: _package_version(name)
            for name in ("numpy", "PyQt6", "PySide6", "qtpy", "pyqtgraph", "napari", "vispy")
        },
    }

    try:
        import psutil
        from qtpy import API_NAME
        from qtpy.QtWidgets import QApplication

        result["qt_api"] = API_NAME
        process = psutil.Process()
        result["rss_process_start_mb"] = process.memory_info().rss / (1024**2)

        fixtures_started = time.perf_counter_ns()
        fixtures = _make_fixture_ring(args.width, args.height, args.ring_size)
        result["fixture_build_ms"] = (
            time.perf_counter_ns() - fixtures_started
        ) / 1_000_000
        result["rss_after_fixtures_mb"] = process.memory_info().rss / (1024**2)

        app = QApplication.instance() or QApplication([])
        holder: dict[str, BenchmarkRunner] = {}

        def presented(frame_id: int) -> None:
            runner = holder.get("runner")
            if runner is not None:
                runner.presented(frame_id)

        backend_started = time.perf_counter_ns()
        backend = _create_backend(args.worker, fixtures[0], presented)
        result["backend_init_ms"] = (
            time.perf_counter_ns() - backend_started
        ) / 1_000_000
        result["rss_after_backend_mb"] = process.memory_info().rss / (1024**2)
        result["worker_start_to_ready_ms"] = (
            time.perf_counter_ns() - worker_started_ns
        ) / 1_000_000

        backend.widget.resize(args.widget_width, args.widget_height)
        runner = BenchmarkRunner(
            app=app,
            backend_name=args.worker,
            backend=backend,
            fixtures=fixtures,
            frames=args.frames,
            warmup_frames=args.warmup_frames,
            fps=args.fps,
            screenshot=Path(args.screenshot),
            result=result,
        )
        holder["runner"] = runner
        runner.start()
        exit_code = app.exec()
        result["qt_exit_code"] = exit_code
    except BaseException as exc:
        result.update(
            {
                "status": "error",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        )

    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result.get("status") == "ok" else 1


def _fmt(value: Any, decimals: int = 2) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{decimals}f}"
    return str(value)


def _write_markdown(path: Path, results: list[dict[str, Any]], args: argparse.Namespace) -> None:
    lines = [
        "# Image viewer backend benchmark",
        "",
        (
            f"Workload: {args.width}x{args.height}, {args.fps:g} fps, "
            f"{args.frames} measured frames after {args.warmup_frames} warmup frames, "
            "three raster layers."
        ),
        "",
        (
            "Latency boundaries are backend-specific draw-completion hooks, not "
            "physical display scan-out. Compare the `presentation_boundary` field "
            "before interpreting small differences."
        ),
        "",
        "| Backend | Status | p50 ms | p95 ms | Drop % | Deadline miss % | Peak RSS MB | Init ms | Process wall s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        latency = result.get("latency_ms", {})
        lines.append(
            "| {backend} | {status} | {p50} | {p95} | {drop} | {miss} | {rss} | {init} | {wall} |".format(
                backend=result.get("backend"),
                status=result.get("status"),
                p50=_fmt(latency.get("p50")),
                p95=_fmt(latency.get("p95")),
                drop=_fmt(
                    100 * result["drop_rate"]
                    if result.get("drop_rate") is not None
                    else None
                ),
                miss=_fmt(
                    100 * result["deadline_miss_rate"]
                    if result.get("deadline_miss_rate") is not None
                    else None
                ),
                rss=_fmt(result.get("rss_peak_mb")),
                init=_fmt(result.get("backend_init_ms")),
                wall=_fmt(result.get("controller_process_wall_s")),
            )
        )
    lines.extend(["", "## Measurement boundaries", ""])
    for result in results:
        lines.append(
            f"- **{result.get('backend')}**: "
            f"{result.get('presentation_boundary', result.get('error', 'failed before initialization'))}"
        )
    lines.extend(
        [
            "",
            "Raw JSON, worker logs, and screenshots are in the same results directory.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _controller(args: argparse.Namespace) -> int:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    output_dir = Path(args.output or f"tests/results/image-viewers-{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    all_results: list[dict[str, Any]] = []

    for backend in args.backends:
        result_path = output_dir / f"{backend}.json"
        screenshot_path = output_dir / f"{backend}.png"
        log_path = output_dir / f"{backend}.log"
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            backend,
            "--result",
            str(result_path),
            "--screenshot",
            str(screenshot_path),
            "--width",
            str(args.width),
            "--height",
            str(args.height),
            "--widget-width",
            str(args.widget_width),
            "--widget-height",
            str(args.widget_height),
            "--fps",
            str(args.fps),
            "--frames",
            str(args.frames),
            "--warmup-frames",
            str(args.warmup_frames),
            "--ring-size",
            str(args.ring_size),
        ]
        environment = os.environ.copy()
        if args.offscreen:
            environment["QT_QPA_PLATFORM"] = "offscreen"
        else:
            environment.pop("QT_QPA_PLATFORM", None)

        started = time.perf_counter()
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=environment,
            timeout=args.timeout,
            check=False,
        )
        process_wall_s = time.perf_counter() - started
        log_path.write_text(
            f"COMMAND: {subprocess.list2cmdline(command)}\n"
            f"EXIT CODE: {completed.returncode}\n\n"
            f"STDOUT:\n{completed.stdout}\n\nSTDERR:\n{completed.stderr}",
            encoding="utf-8",
        )
        if result_path.exists():
            result = json.loads(result_path.read_text(encoding="utf-8"))
        else:
            result = {
                "backend": backend,
                "status": "error",
                "error": "Worker exited without writing a result file",
            }
        result["controller_process_wall_s"] = process_wall_s
        result["worker_exit_code"] = completed.returncode
        result["log"] = str(log_path)
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        all_results.append(result)
        print(
            f"{backend:11} {result.get('status'):5} "
            f"p95={_fmt(result.get('latency_ms', {}).get('p95')):>8} ms "
            f"drop={_fmt(100 * result['drop_rate'] if result.get('drop_rate') is not None else None):>6}%"
        )

    combined_path = output_dir / "results.json"
    combined_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    report_path = output_dir / "README.md"
    _write_markdown(report_path, all_results, args)
    print(f"\nReport: {report_path.resolve()}")
    return 0 if all(result.get("status") == "ok" for result in all_results) else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backends", nargs="+", choices=BACKENDS, default=list(BACKENDS))
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--widget-width", type=int, default=960)
    parser.add_argument("--widget-height", type=int, default=600)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--frames", type=int, default=180)
    parser.add_argument("--warmup-frames", type=int, default=30)
    parser.add_argument("--ring-size", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--offscreen",
        action="store_true",
        help="Use Qt offscreen mode for smoke tests; do not rank renderer performance.",
    )
    parser.add_argument("--worker", choices=BACKENDS, help=argparse.SUPPRESS)
    parser.add_argument("--result", help=argparse.SUPPRESS)
    parser.add_argument("--screenshot", help=argparse.SUPPRESS)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.width <= 0 or args.height <= 0:
        raise SystemExit("width and height must be positive")
    if args.frames <= 0 or args.warmup_frames < 0 or args.ring_size <= 0:
        raise SystemExit("frames/ring-size must be positive and warmup non-negative")
    if args.fps <= 0:
        raise SystemExit("fps must be positive")
    if args.worker:
        if not args.result or not args.screenshot:
            raise SystemExit("worker mode requires --result and --screenshot")
        return _worker(args)
    return _controller(args)


if __name__ == "__main__":
    raise SystemExit(main())
