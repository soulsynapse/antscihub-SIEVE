from __future__ import annotations

import math
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from antscihub_sieve.media.session import MediaSession


def latency_summary(samples_ms: list[float]) -> dict[str, Any]:
    ordered = sorted(samples_ms)
    if not ordered:
        return {
            "count": 0,
            "median_ms": None,
            "p95_ms": None,
            "samples_ms": [],
        }
    p95_index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return {
        "count": len(ordered),
        "median_ms": statistics.median(ordered),
        "p95_ms": ordered[p95_index],
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
        "samples_ms": samples_ms,
    }


def ffmpeg_version() -> str:
    completed = subprocess.run(
        ["ffmpeg", "-version"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.splitlines()[0] if completed.stdout else "unknown"


def environment_metadata() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor(),
        "ffmpeg": ffmpeg_version(),
    }


def timed_read(
    session: MediaSession, frame: int, max_width: int | None
) -> tuple[bytes, float]:
    started = time.perf_counter_ns()
    raw = session.read_frame_rgb(frame, max_width=max_width)
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    return raw, elapsed_ms


def benchmark_media(
    path: Path,
    *,
    asset: dict[str, Any] | None = None,
    iterations: int = 3,
    sequential_frames: int = 12,
    max_width: int | None = 1280,
) -> dict[str, Any]:
    """Measure user-relevant open, sequential-read, and random-seek behavior."""
    path = path.resolve()
    if iterations < 1:
        raise ValueError("iterations must be at least 1")
    if sequential_frames < 2:
        raise ValueError("sequential_frames must be at least 2")
    if max_width is not None and max_width < 1:
        raise ValueError("max_width must be positive")

    open_probe_ms: list[float] = []
    open_first_frame_ms: list[float] = []
    metadata: dict[str, Any] | None = None
    for _ in range(iterations):
        started = time.perf_counter_ns()
        session = MediaSession(path)
        probe_finished = time.perf_counter_ns()
        try:
            session.read_frame_rgb(0, max_width=max_width)
            first_frame_finished = time.perf_counter_ns()
        finally:
            session.close()
        open_probe_ms.append((probe_finished - started) / 1_000_000)
        open_first_frame_ms.append(
            (first_frame_finished - started) / 1_000_000
        )
        metadata = session.metadata
    assert metadata is not None

    session = MediaSession(path)
    try:
        frame_count = session.frame_count
        sequential_count = min(sequential_frames, frame_count)
        _, sequential_startup_ms = timed_read(session, 0, max_width)
        sequential_ms: list[float] = []
        for frame in range(1, sequential_count):
            _, elapsed_ms = timed_read(session, frame, max_width)
            sequential_ms.append(elapsed_ms)

        random_positions = list(
            dict.fromkeys(
                min(
                    frame_count - 1,
                    max(0, round((frame_count - 1) * fraction)),
                )
                for fraction in (0.9, 0.1, 0.5)
            )
        )
        random_ms: list[float] = []
        for _ in range(iterations):
            for frame in random_positions:
                _, elapsed_ms = timed_read(session, frame, max_width)
                random_ms.append(elapsed_ms)
        output_size = session.scaled_dimensions(max_width)
    finally:
        session.close()

    sequential_summary = latency_summary(sequential_ms)
    native_fps = int(metadata["fps_num"]) / int(metadata["fps_den"])
    frame_budget_ms = 1000 / native_fps
    median_value = sequential_summary["median_ms"]
    median_decode_ms = float(median_value) if median_value is not None else None
    estimated_capacity_fps = (
        1000 / median_decode_ms if median_decode_ms is not None else None
    )
    realtime_factor = (
        estimated_capacity_fps / native_fps
        if estimated_capacity_fps is not None
        else None
    )
    media_identity = {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "asset_id": asset.get("asset_id") if asset else None,
        "content_sha256": (
            asset.get("media", {}).get("content_sha256") if asset else None
        ),
        "codec": metadata.get("codec"),
        "pixel_format": metadata.get("pixel_format"),
        "source_width": metadata.get("width"),
        "source_height": metadata.get("height"),
        "fps_num": metadata.get("fps_num"),
        "fps_den": metadata.get("fps_den"),
        "frame_count": frame_count,
        "frame_count_status": (
            "verified"
            if metadata.get("decoded_frame_count") is not None
            else "estimated"
        ),
        "duration_seconds": metadata.get("duration_seconds"),
    }
    return {
        "schema_version": 1,
        "kind": "media_performance_estimate",
        "environment": environment_metadata(),
        "asset": media_identity,
        "representation": {
            "kind": "native" if max_width is None else "display",
            "max_width": max_width,
            "decoded_width": output_size[0],
            "decoded_height": output_size[1],
        },
        "configuration": {
            "iterations": iterations,
            "sequential_frames": sequential_count,
            "random_positions": random_positions,
            "cache_state": (
                "new MediaSession per open sample; OS filesystem cache "
                "not flushed"
            ),
        },
        "measurements": {
            "open_probe": latency_summary(open_probe_ms),
            "open_to_first_frame": latency_summary(open_first_frame_ms),
            "decoder_startup": latency_summary([sequential_startup_ms]),
            "adjacent_sequential_read": sequential_summary,
            "random_seek": latency_summary(random_ms),
        },
        "estimate": {
            "native_rate_fps": native_fps,
            "frame_budget_ms": frame_budget_ms,
            "sequential_capacity_fps": estimated_capacity_fps,
            "realtime_factor": realtime_factor,
            "keeps_up_with_native_rate": (
                median_decode_ms <= frame_budget_ms
                if median_decode_ms is not None
                else None
            ),
            "scope": (
                "media-service decode only; excludes GUI paint, overlays, "
                "and scientific processing"
            ),
        },
    }


def format_media_benchmark(result: dict[str, Any]) -> str:
    asset = result["asset"]
    representation = result["representation"]
    measurements = result["measurements"]
    estimate = result["estimate"]
    lines = [
        f"Media performance estimate: {Path(asset['path']).name}",
        (
            "Representation: "
            f"{representation['kind']} "
            f"{representation['decoded_width']}×"
            f"{representation['decoded_height']}"
        ),
        (
            "Open to first frame: "
            f"{measurements['open_to_first_frame']['median_ms']:.1f} ms "
            f"median"
        ),
        (
            "Adjacent frames: "
            f"{measurements['adjacent_sequential_read']['median_ms']:.2f} ms "
            f"median, "
            f"{measurements['adjacent_sequential_read']['p95_ms']:.2f} ms p95"
            if measurements["adjacent_sequential_read"]["median_ms"] is not None
            else "Adjacent frames: unavailable (asset has fewer than 2 frames)"
        ),
        (
            "Random seek: "
            f"{measurements['random_seek']['median_ms']:.1f} ms median"
        ),
        (
            "Estimated media-service sequential capacity: "
            f"{estimate['sequential_capacity_fps']:.1f} fps "
            f"({estimate['realtime_factor']:.2f}× native rate)"
            if estimate["sequential_capacity_fps"] is not None
            else "Estimated media-service sequential capacity: unavailable"
        ),
        (
            "Media service fits the native frame budget: "
            + (
                "yes"
                if estimate["keeps_up_with_native_rate"]
                else (
                    "no"
                    if estimate["keeps_up_with_native_rate"] is not None
                    else "unknown"
                )
            )
        ),
        f"Estimate scope: {estimate['scope']}.",
        (
            "Cache note: "
            f"{result['configuration']['cache_state']}."
        ),
    ]
    return "\n".join(lines)
