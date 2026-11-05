"""Frames surviving a remux of a raw H.264 stream into MP4: a synthetic clip encoded with and
without B-frames, remuxed with -c copy, with +genpts, and re-encoded; counted by ffprobe and by
reading every frame with cv2. Prints the table docs/findings/2026-11-04-raw-remux.md holds."""
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

FRAMES = 60
ff, fp = shutil.which("ffmpeg"), shutil.which("ffprobe")


def counts(path):
    out = subprocess.run([fp, "-v", "error", "-count_frames", "-select_streams", "v", "-show_entries",
                          "stream=nb_frames,nb_read_frames", "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout.strip()
    cap = cv2.VideoCapture(str(path), cv2.CAP_FFMPEG)
    n = 0
    while cap.read()[0]:
        n += 1
    return f"ffprobe {out:<6} cv2 header {int(cap.get(cv2.CAP_PROP_FRAME_COUNT)):>4} decoded {n}"


def main():
    tmp = Path(tempfile.mkdtemp())
    video = tmp / "v.avi"
    w = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 30, (64, 48))
    for i in range(300):
        w.write(np.full((48, 64, 3), i % 256, np.uint8))
    w.release()
    for bf in ("3", "0"):
        raw = tmp / f"bf{bf}.h264"
        subprocess.check_call([ff, "-y", "-loglevel", "error", "-i", str(video), "-frames:v", str(FRAMES), "-vf", "format=yuv420p",
                               "-c:v", "libx264", "-g", "4", "-bf", bf, "-f", "h264", str(raw)])
        print(f"raw, bf={bf}:            {counts(raw)}")
        for tag, pre, post in (("copy", [], ["-c", "copy"]), ("copy +genpts", ["-fflags", "+genpts"], ["-c", "copy"]),
                               ("re-encode crf 18", [], ["-c:v", "libx264", "-crf", "18"])):
            out = tmp / f"bf{bf}-{tag.replace(' ', '_')}.mp4"
            subprocess.check_call([ff, "-y", "-loglevel", "error", *pre, "-framerate", "30", "-i", str(raw), *post, str(out)])
            print(f"  {tag:<22} {counts(out)}")


if __name__ == "__main__":
    main()
