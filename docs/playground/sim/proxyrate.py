"""What a display proxy of a frame costs: bytes held, milliseconds to make and to show again.

Run: python docs/playground/sim/proxyrate.py <clip> [frames]. It reads frames of the clip and of
the same frames enlarged to 5.3K, and changes nothing on disk.
"""
import sys
import time

import cv2
import numpy as np

SHOWN = (1280, 720)   # a display's worth of pixels; the player scales to its widget each paint


def timed(act, over):
    began = time.perf_counter()
    out = [act(x) for x in over]
    return out, (time.perf_counter() - began) / len(over) * 1000


def main(path, count=60):
    clip = cv2.VideoCapture(path)
    frames = [f for ok, f in (clip.read() for _ in range(count)) if ok]
    clip.release()
    for label, full in (("as read", frames), ("at 5.3K", [cv2.resize(f, (5312, 2988)) for f in frames[:20]])):
        h, w = full[0].shape[:2]
        print(f"{label}: {w}x{h}, {full[0].nbytes / 1e6:.1f} MB a frame")
        small, shrink = timed(lambda f: cv2.resize(f, SHOWN, interpolation=cv2.INTER_AREA), full)
        print(f"  shrunk to {SHOWN[0]}x{SHOWN[1]}: {small[0].nbytes / 1e6:.2f} MB, {shrink:.2f} ms to make")
        for quality in (70, 85, 95):
            packed, pack = timed(lambda f: cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, quality])[1], small)
            back, unpack = timed(lambda b: cv2.imdecode(b, cv2.IMREAD_COLOR), packed)
            worst = max(float(np.abs(a.astype(np.int16) - b).mean()) for a, b in zip(small, back))
            print(f"  jpeg {quality}: {np.mean([len(p) for p in packed]) / 1e3:.0f} KB, {shrink + pack:.2f} ms to make "
                  f"from the frame, {unpack:.2f} ms to show, mean error {worst:.2f} of 255")
        packed, pack = timed(lambda f: cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, 85])[1], full)
        _, unpack = timed(lambda b: cv2.imdecode(b, cv2.IMREAD_COLOR), packed)
        print(f"  full size jpeg 85: {np.mean([len(p) for p in packed]) / 1e3:.0f} KB, {pack:.2f} ms to make, {unpack:.2f} ms to show")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 60)
