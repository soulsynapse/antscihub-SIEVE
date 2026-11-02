"""Experiment behind docs/findings/2026-11-02-kinematics-and-spacing.md: what the loose ants' speeds
and headings and the rows' spacing read on a document's settings.

    .venv\Scripts\python -X utf8 docs\findings\experiments\2026-11-02-kinematics-and-spacing.py [document] [start] [rows]

Reads the video, threshold, blobs and track params from the document (default
video-tests/purb-settings.json), decodes the rows once, detects and links as the GUI would, then
runs kinematics over the tracks and spacing over the blobs. Loose is outside the cluster box the
diagnostics finding drew; records inside it are the split's pieces of the pile.
"""
import json
import os
import sys
import time

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from sieve_player import Decoder  # noqa: E402
from tools import blobs, kinematics, spacing, track  # noqa: E402

DOC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "video-tests", "purb-settings.json")
START = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
ROWS = int(sys.argv[3]) if len(sys.argv) > 3 else 600
CLUSTER = (330, 160, 520, 300)   # x0, y0, x1, y1 at scale 0.5, from 2026-11-01-track-diagnostics.md


def params(doc, tool):
    return next(n["params"] for n in doc["nodes"] if n["tool"] == tool)


def pct(a, q=(5, 50, 95)):
    a = np.asarray(a, np.float64)
    return "none" if len(a) == 0 else "  ".join(f"p{p} {np.percentile(a, p):.2f}" for p in q)


def loose(t):
    x0, y0, x1, y1 = CLUSTER
    return t[~((t["cx"] >= x0) & (t["cx"] < x1) & (t["cy"] >= y0) & (t["cy"] < y1))]


def main():
    doc = json.load(open(DOC, encoding="utf-8"))
    v, th, bp, tp = params(doc, "video"), params(doc, "threshold"), params(doc, "blobs"), params(doc, "track")
    dec = Decoder(doc["video"])
    dec.output, dec.scale = v.get("output", "luma"), float(v.get("scale", 1.0))
    print(f"{doc['video']}: {dec.width}x{dec.height} @ {dec.fps:.2f} fps; rows {START}..{START + ROWS - 1} at {dec.scale}; "
          f"threshold {th}; blobs {bp}; track {tp}")
    frames = [dec.read(r) for r in range(START, START + ROWS)]
    dec.close()
    flag = cv2.THRESH_BINARY_INV if th.get("invert") else cv2.THRESH_BINARY
    tables = [blobs.find(cv2.threshold(f, int(th["thresh"]), 255, flag)[1], int(bp["min_area"]), int(bp["max_area"]),
                         255 - f, int(bp["core_threshold"]), bool(bp["split"])) for f in frames]
    tracks, _ = track.link(tables, float(tp["max_step"]), int(tp["lost_rows"]), int(tp["min_rows"]), float(tp["min_p"]))
    t0 = time.perf_counter()
    kin = kinematics.kinematics(tracks)
    print(f"kinematics over {ROWS} rows: {(time.perf_counter() - t0) * 1000:.0f} ms")
    la = np.concatenate([loose(t) for t in kin])
    la = la[~np.isnan(la["speed"])]
    moving = la[la["speed"] > 0.5]
    diff = np.abs(((moving["heading"] - moving["angle"]) + 90) % 180 - 90)
    print(f"loose records with a step {len(la)}: speed px/row {pct(la['speed'], (5, 50, 95, 99))}; over 0.5 px/row {np.mean(la['speed'] > 0.5) * 100:.1f}%")
    print(f"moving ones {len(moving)}: |heading - angle| mod 180 {pct(diff, (50, 90, 95))} deg; within 20 deg {np.mean(diff <= 20) * 100:.1f}%; "
          f"within 45 deg {np.mean(diff <= 45) * 100:.1f}%")
    fast = la[la["speed"] > 2]
    print(f"records over 2 px/row {len(fast)}: speed {pct(fast['speed'], (50, 95, 100))}")
    lt = [loose(t) for t in tables]
    for m in ("min", "mean"):
        t0 = time.perf_counter()
        all_, lo = [spacing.spacing(t, m) for t in tables], [spacing.spacing(t, m) for t in lt]
        print(f"spacing {m}, all blobs: {pct(all_)} px in {(time.perf_counter() - t0) * 1000:.0f} ms; loose only: {pct(lo)} px")
    for r in (10, 20, 40):
        all_, lo = [spacing.spacing(t, "pairs", r) for t in tables], [spacing.spacing(t, "pairs", r) for t in lt]
        print(f"pairs within {r} px a row: all blobs mean {np.mean(all_):.2f}, rows with any {np.mean(np.array(all_) > 0) * 100:.0f}%; "
              f"loose only mean {np.mean(lo):.2f}, rows with any {np.mean(np.array(lo) > 0) * 100:.0f}%")


if __name__ == "__main__":
    main()
