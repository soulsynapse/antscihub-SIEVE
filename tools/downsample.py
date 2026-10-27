"""Frame tool: downsample a video in space (scale) and time (keep every Nth frame).

Inside the player the loop window previews the result: the frame is resized, and dropped rows
hold the last kept one so playback at source fps looks like playback at fps/N. The hold is by row
index; the export's `fps=` filter resamples by timestamp, so on a variable-rate source the two can
differ by a frame here and there.

    python tools/downsample.py                 # opens empty; pick a video in Inputs
    python tools/downsample.py video.mp4       # preloads it
    python tools/downsample.py video.mp4 --scale 0.5 --every 2 --out small.mp4   # no Qt

run() needs only cv2 and numpy; Qt and sieve_player are imported inside settings().
"""
import os
import shutil
import subprocess
import sys

import cv2

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "downsample", "frame", ("bgr", "gray", "mask"), "same"
DEFAULTS = {"scale": 0.5, "every": 2}


def run(frames, row, params):
    n = max(1, int(params["every"]))
    f = frames(row - row % n)  # dropped rows hold the last kept one
    s = params["scale"]
    if s == 1.0:
        return f
    h, w = f.shape[:2]
    return cv2.resize(f, (max(2, int(w * s) // 2 * 2), max(2, int(h * s) // 2 * 2)), interpolation=cv2.INTER_AREA)


def ffmpeg_command(src, dst, scale, every, fps):
    """The ffmpeg call that writes what run() previews. Even output dims, since yuv420p needs them."""
    vf = f"fps={fps / every:.6f},scale=trunc(iw*{scale}/2)*2:trunc(ih*{scale}/2)*2"
    return [shutil.which("ffmpeg") or "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats",
            "-i", str(src), "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an", str(dst)]


def export(src, dst, scale, every):
    """Headless export; blocks until ffmpeg is done. Raises CalledProcessError on failure."""
    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()
    subprocess.run(ffmpeg_command(src, dst, scale, every, fps), check=True)


def settings(parent=None):
    from sieve_player import ParamWidget

    w = ParamWidget(parent)
    w.layout().setContentsMargins(0, 0, 0, 0)
    w.add_float("scale", 0.1, 1.0, DEFAULTS["scale"])
    w.add_int("every", 1, 10, DEFAULTS["every"])
    return w


def output_name(src, params):
    root, _ = os.path.splitext(str(src))
    return f"{root}_x{params['scale']:g}_every{params['every']}.mp4"


def export_command(src, dst, params, fps):
    return ffmpeg_command(src, dst, params["scale"], params["every"], fps)


def describe_output(src, params, fps):
    from sieve_player import probe  # GUI side only

    w, h, _, n = probe(src)
    s, k = params["scale"], params["every"]
    return f"{int(w * s) // 2 * 2}×{int(h * s) // 2 * 2}   {fps / k:.2f} fps   ~{n // k} frames"


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("video", nargs="?")
    ap.add_argument("--scale", type=float, default=DEFAULTS["scale"])
    ap.add_argument("--every", type=int, default=DEFAULTS["every"])
    ap.add_argument("--out", help="write this file with ffmpeg and exit; no Qt needed")
    a = ap.parse_args()
    if a.out:
        if not a.video:
            ap.error("--out needs a video")
        export(a.video, a.out, a.scale, a.every)
        sys.exit(0)
    from sieve_player import play

    sys.exit(play([sys.modules[__name__]], a.video))
