"""The fastest route to a luma frame off the 5.3K source, including libav with no Python in the loop.

Experiment 01 established parity between cv2 and PyAV on threaded sequential
decode. This asks what actually sets the ceiling: codec thread count, hardware
decode (and its download, priced rather than assumed), keyframe-only decode
for the filmstrip pre-pass, and ffmpeg run as a subprocess — both piping gray
rawvideo into Python (the honest end-to-end, pipe cost included) and decoding
to a null sink (the pure-decode ceiling with no pipe and no Python).

Null-sink cases time whole runs rather than frames, because ffmpeg exposes no
per-frame boundary from outside; their unit says so. Hardware cases capture
ffmpeg's stderr into the case note, because -hwaccel falls back to software
silently and a silent fallback reads as 'hardware buys nothing'.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import av

from harness import FOOTAGE, Run, report, time_case

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
FRAMES = 300
W, H = 5312, 2988


def pyav_luma(path: Path, frames: int, thread_count: int = 0):
    def work():
        import numpy as np

        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"
            stream.codec_context.thread_count = thread_count
            yield "open"
            for index, frame in enumerate(container.decode(stream)):
                if index >= frames:
                    break
                plane = frame.planes[0]
                arr = np.frombuffer(plane, dtype=np.uint8)
                arr = arr[: frame.height * plane.line_size]
                arr = arr.reshape(frame.height, plane.line_size)[:, : frame.width]
                arr[0, 0]
                yield True

    return work


def pyav_keyframes_only(path: Path, max_frames: int):
    def work():
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"
            stream.codec_context.skip_frame = "NONKEY"
            yield "open"
            for index, _frame in enumerate(container.decode(stream)):
                if index >= max_frames:
                    break
                yield True

    return work


def pyav_hwaccel(path: Path, frames: int, device: str):
    def work():
        from av.codec.hwaccel import HWAccel

        hw = HWAccel(device_type=device, allow_software_fallback=False)
        with av.open(str(path), hwaccel=hw) as container:
            stream = container.streams.video[0]
            yield "open"
            for index, frame in enumerate(container.decode(stream)):
                if index >= frames:
                    break
                work.fmt = frame.format.name
                yield True

    return work


def ffmpeg_pipe_gray(path: Path, frames: int, hwaccel: str | None, vf: str, w: int, h: int):
    def work():
        cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-v", "error"]
        if hwaccel:
            cmd += ["-hwaccel", hwaccel]
        cmd += ["-i", str(path), "-frames:v", str(frames), "-vf", vf,
                "-f", "rawvideo", "pipe:1"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)
        need = w * h
        yield "open"
        while True:
            buf = proc.stdout.read(need)
            if buf is None or len(buf) < need:
                break
            yield True
        proc.wait()

    return work


def ffmpeg_null(path: Path, frames: int, hwaccel: str | None, runs: int = 4):
    def work():
        cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-v", "warning", "-y"]
        if hwaccel:
            cmd += ["-hwaccel", hwaccel]
        cmd += ["-i", str(path), "-map", "0:v:0", "-frames:v", str(frames),
                "-f", "null", "-"]
        yield "start"
        for _ in range(runs):
            r = subprocess.run(cmd, stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE)
            work.stderr = r.stderr.decode(errors="replace").strip()
            if r.returncode != 0:
                work.failed = True
                return
            yield True

    return work


def main() -> None:
    run = Run(
        experiment="03-fastest-luma",
        question=(
            "What sets the ceiling on sequential luma off the 5.3K HEVC "
            "source: threads, hardware, keyframe-only, or leaving Python out "
            "entirely?"
        ),
    )
    run.add_footage(BIG)

    for tc in (1, 2, 4, 8, 16, 0):
        n = 120 if tc <= 2 else FRAMES
        time_case(
            run, f"pyav/luma/threads={tc or 'auto'}", pyav_luma(BIG, n, tc),
            params={"backend": "pyav", "thread_count": tc, "frames": n},
        )

    time_case(
        run, "pyav/keyframes-only", pyav_keyframes_only(BIG, 40),
        params={"backend": "pyav", "skip_frame": "NONKEY"},
        unit="ms per keyframe",
        note="demux of the skipped frames is included; that is the pre-pass cost",
    )

    for device in ("d3d11va", "cuda"):
        work = pyav_hwaccel(BIG, 200, device)
        try:
            case = time_case(
                run, f"pyav/hwaccel/{device}", work,
                params={"backend": "pyav", "hwaccel": device},
            )
            fmt = getattr(work, "fmt", "?")
            on_gpu = fmt in ("d3d11", "cuda", "vulkan", "dxva2_vld")
            case.note = (
                f"decoder output format {fmt}: "
                + ("frames stay on GPU; download not priced here" if on_gpu
                   else "a system-memory format, so the transfer is included")
            )
        except Exception as exc:  # noqa: BLE001 - absence is the datum
            run.note(f"pyav hwaccel {device} did not run: {exc!r}")

    full = f"format=gray"
    display = "scale=1328:747,format=gray"
    for hw in (None, "d3d11va"):
        tag = hw or "sw"
        time_case(
            run, f"ffmpeg-pipe/{tag}/gray-full", ffmpeg_pipe_gray(BIG, FRAMES, hw, full, W, H),
            params={"backend": "ffmpeg-cli", "hwaccel": hw, "vf": full},
            note="includes piping w*h bytes/frame into Python; pipe may bound it",
        )
    time_case(
        run, "ffmpeg-pipe/sw/gray-display", ffmpeg_pipe_gray(BIG, FRAMES, None, display, 1328, 747),
        params={"backend": "ffmpeg-cli", "hwaccel": None, "vf": display},
        note="the display-size pushdown: scale+gray inside libavfilter",
    )

    for hw in (None, "d3d11va", "cuda"):
        tag = hw or "sw"
        work = ffmpeg_null(BIG, FRAMES, hw)
        case = time_case(
            run, f"ffmpeg-null/{tag}", work,
            params={"backend": "ffmpeg-cli", "hwaccel": hw, "frames_per_run": FRAMES},
            warmup=1, unit=f"ms per {FRAMES}-frame run",
        )
        err = getattr(work, "stderr", "")
        if getattr(work, "failed", False):
            case.note = f"did not run: {err[:160]}"
        elif err:
            case.note = f"stderr: {err[:160]}"

    for case in run.cases:
        report(case)
    print(f"\nwrote {run.write()}")


if __name__ == "__main__":
    main()
