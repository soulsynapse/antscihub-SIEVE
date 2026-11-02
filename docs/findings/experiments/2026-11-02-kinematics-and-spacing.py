"""Experiment behind docs/findings/2026-11-02-kinematics-and-spacing.md: what the loose ants' speeds
and headings and the rows' spacing read on a document's settings.

    .venv\Scripts\python -X utf8 docs\findings\experiments\2026-11-02-kinematics-and-spacing.py [document] [start] [rows] [picture.png]

Reads the video, threshold, blobs and track params from the document (default
video-tests/purb-settings.json), decodes the rows once, detects and links as the GUI would, then
runs kinematics over the tracks at each span and spacing over the blobs. Loose is outside the
cluster box the diagnostics finding drew; records inside it are the split's pieces of the pile.
The heading is set against the moment axis on the moving records, and with a picture path given,
eight ten-row cases spread from worst to best agreement are drawn to it, the axis in yellow and the
step as a red arrow.
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
PICTURE = sys.argv[4] if len(sys.argv) > 4 else None
CLUSTER = (330, 160, 520, 300)   # x0, y0, x1, y1 at scale 0.5, from 2026-11-01-track-diagnostics.md


def params(doc, tool):
    return next(n["params"] for n in doc["nodes"] if n["tool"] == tool)


def pct(a, q=(5, 50, 95)):
    a = np.asarray(a, np.float64)
    return "none" if len(a) == 0 else "  ".join(f"p{p} {np.percentile(a, p):.2f}" for p in q)


def loose(t):
    x0, y0, x1, y1 = CLUSTER
    return t[~((t["cx"] >= x0) & (t["cx"] < x1) & (t["cy"] >= y0) & (t["cy"] < y1))]


def picture(frames, kin, moving, diff):
    """Eight of `moving`, spread from worst to best agreement, cut 80 px about the centroid at four
    times the size, the moment axis in yellow and the step as a red arrow ending on the centroid."""
    order = np.argsort(-diff)
    tiles = []
    for b, d in ((moving[i], diff[i]) for i in order[:: max(1, len(order) // 8)][:8]):
        cx, cy = int(round(float(b["cx"]))), int(round(float(b["cy"])))
        r = next(r for r, t in enumerate(kin) if len(t) and np.any((t["id"] == b["id"]) & (t["cx"] == b["cx"]) & (t["cy"] == b["cy"])))
        x0, y0 = max(cx - 40, 0), max(cy - 40, 0)
        crop = cv2.resize(cv2.cvtColor(frames[r][y0:cy + 40, x0:cx + 40], cv2.COLOR_GRAY2BGR), None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
        c = (cx - x0) * 4, (cy - y0) * 4
        a = np.radians(float(b["angle"]))
        cv2.line(crop, (int(c[0] - 60 * np.cos(a)), int(c[1] - 60 * np.sin(a))), (int(c[0] + 60 * np.cos(a)), int(c[1] + 60 * np.sin(a))), (0, 255, 255), 2)
        cv2.arrowedLine(crop, (int(c[0] - 40 * b["dx"]), int(c[1] - 40 * b["dy"])), c, (0, 0, 255), 2, tipLength=0.3)
        cv2.putText(crop, f"r{r + START} id{int(b['id'])} {d:.0f} deg", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        pad = np.zeros((320, 320, 3), np.uint8)
        pad[:crop.shape[0], :crop.shape[1]] = crop
        tiles.append(pad)
    cv2.imwrite(PICTURE, np.vstack([np.hstack(tiles[:4]), np.hstack(tiles[4:])]) if len(tiles) == 8 else np.hstack(tiles))
    print(f"  picture of eight ten-row cases: {PICTURE}")


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
    print(f"loose records with a step {len(la)}: speed px/row {pct(la['speed'], (5, 50, 95, 99))}; over 0.5 px/row {np.mean(la['speed'] > 0.5) * 100:.1f}%; "
          f"over 2 px/row {np.sum(la['speed'] > 2)}, their speed {pct(la[la['speed'] > 2]['speed'], (50, 95, 100))}")
    print("heading against the moment axis, loose records under 1000 px moving at least 3 px and 0.3 px a row over the span:")
    for span in (1, 3, 5, 10, 20, 30):
        kin = kinematics.kinematics(tracks, span)
        la = np.concatenate([loose(t) for t in kin])
        la = la[~np.isnan(la["speed"]) & (la["area"] <= 1000) & (la["speed"] * span >= 3) & (la["speed"] >= 0.3)]
        diff = np.abs(((la["heading"] - la["angle"]) + 90) % 180 - 90)
        moved = la["speed"] * span
        bands = ", ".join(f"{lo}..{hi} {np.mean(diff[(moved >= lo) & (moved < hi)] <= 20) * 100:.0f}% of {np.sum((moved >= lo) & (moved < hi))}"
                          for lo, hi in ((3, 5), (5, 10), (10, 20), (20, 1e9)))
        print(f"  span {span:2d}: moving {len(la):4d}; |heading - angle| mod 180 {pct(diff, (50, 90))} deg; within 20 deg {np.mean(diff <= 20) * 100:.0f}%"
              + (f"; by px moved {bands}" if span == 10 else ""))
        if span == 10 and PICTURE:
            picture(frames, kin, la, diff)
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
