from __future__ import annotations

import json
import subprocess
import threading
from fractions import Fraction
from pathlib import Path
from typing import Any

from antscihub_sieve.errors import SieveError
from antscihub_sieve.media.process import CREATE_NO_WINDOW


def run_ffprobe(path: Path, *, count_frames: bool = False, count_packets: bool = False,
                cancel_event: threading.Event | None = None) -> dict[str, Any]:
    args = ["ffprobe", "-v", "error", "-select_streams", "v:0"]
    if count_frames:
        args.append("-count_frames")
    if count_packets:
        args.append("-count_packets")
    args += ["-show_streams", "-show_format", "-of", "json", str(path)]
    try:
        if cancel_event is None:
            completed = subprocess.run(args, capture_output=True, text=True, check=False, creationflags=CREATE_NO_WINDOW)
        else:
            process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=CREATE_NO_WINDOW)
            while True:
                if cancel_event.is_set():
                    process.terminate(); process.communicate()
                    raise SieveError("DERIVATION_CANCELLED", "Derivation was cancelled", path=str(path))
                try:
                    stdout, stderr = process.communicate(timeout=0.1); break
                except subprocess.TimeoutExpired:
                    continue
            completed = subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
    except OSError as exc:
        raise SieveError("MEDIA_PROBE_FAILED", "ffprobe could not be started", path=str(path), detail=str(exc)) from exc
    if completed.returncode:
        raise SieveError("MEDIA_PROBE_FAILED", "Video probing failed", path=str(path), detail=completed.stderr.strip())
    try:
        data = json.loads(completed.stdout)
        stream = data["streams"][0]
        rate = Fraction(stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0/1")
    except (KeyError, IndexError, ValueError, ZeroDivisionError, json.JSONDecodeError) as exc:
        raise SieveError("MEDIA_PROBE_FAILED", "Video probe did not contain a usable video stream", path=str(path)) from exc
    duration = stream.get("duration") or data.get("format", {}).get("duration") or 0
    frames = stream.get("nb_read_frames") or stream.get("nb_frames")
    packets = stream.get("nb_read_packets")
    return {
        "width": int(stream["width"]), "height": int(stream["height"]),
        "pixel_format": stream.get("pix_fmt", "unknown"), "codec": stream.get("codec_name", "unknown"),
        "fps_num": rate.numerator, "fps_den": rate.denominator,
        "container_frame_count": int(stream["nb_frames"]) if stream.get("nb_frames", "").isdigit() else None,
        "decoded_frame_count": int(frames) if str(frames or "").isdigit() and count_frames else None,
        "packet_frame_count": int(packets) if str(packets or "").isdigit() and count_packets else None,
        "duration_seconds": float(duration),
        "color_range": stream.get("color_range"), "color_space": stream.get("color_space"),
        "color_transfer": stream.get("color_transfer"), "color_primaries": stream.get("color_primaries"),
    }


def expected_frame_count(probe: dict[str, Any]) -> int:
    if probe.get("decoded_frame_count") is not None:
        return int(probe["decoded_frame_count"])
    if probe.get("packet_frame_count") is not None:
        return int(probe["packet_frame_count"])
    if probe.get("container_frame_count") is not None:
        return int(probe["container_frame_count"])
    return max(1, round(float(probe["duration_seconds"]) * int(probe["fps_num"]) / int(probe["fps_den"])))
