"""Experiment behind docs/findings/2026-11-02-morphology.md: what an opening or closing between
threshold and blobs does to the records and the tracks on a document's settings.

    .venv\Scripts\python -X utf8 docs\findings\experiments\2026-11-02-morphology.py [document] [start] [rows]

Reads the video, threshold, blobs and track params from the document (default
video-tests/purb-settings.json), decodes the rows once, thresholds them, and for each morphology
variant runs blobs.find and track.link as the GUI would. Per variant: the op's cost, the mask's
regions a row split by the area bounds, the loose records (outside the cluster box the diagnostics
finding drew) with their area against min_area, and the loose ids' gaps, a gap being rows an id went
unseen between two takes, which is an ant dipping under the threshold.
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
from tools import blobs, morphology, track  # noqa: E402

DOC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "video-tests", "purb-settings.json")
START = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
ROWS = int(sys.argv[3]) if len(sys.argv) > 3 else 600
CLUSTER = (330, 160, 520, 300)   # x0, y0, x1, y1 at scale 0.5, from 2026-11-01-track-diagnostics.md
VARIANTS = (("none", None), ("open r1", ("open", 1, 1)), ("open r1 x2", ("open", 1, 2)),
            ("open r2", ("open", 2, 1)), ("close r1", ("close", 1, 1)), ("close r2", ("close", 2, 1)))


def params(doc, tool):
    return next(n["params"] for n in doc["nodes"] if n["tool"] == tool)


def pct(a, q=(5, 50, 95)):
    a = np.asarray(a, np.float64)
    return "none" if len(a) == 0 else "  ".join(f"p{p} {np.percentile(a, p):.1f}" for p in q)


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
    masks = [cv2.threshold(f, int(th["thresh"]), 255, flag)[1] for f in frames]
    lo, hi = int(bp["min_area"]), int(bp["max_area"])
    ms_, lr, mr, mp = float(tp["max_step"]), int(tp["lost_rows"]), int(tp["min_rows"]), float(tp["min_p"])
    for name, m in VARIANTS:
        t0 = time.perf_counter()
        ms = masks if m is None else [morphology.morph(k, *m) for k in masks]
        op_ms = (time.perf_counter() - t0) * 1000 / ROWS
        regions = np.concatenate([cv2.connectedComponentsWithStats(k, connectivity=8)[2][1:, cv2.CC_STAT_AREA] for k in ms])
        tables = [blobs.find(k, lo, hi, 255 - f, int(bp["core_threshold"]), bool(bp["split"])) for k, f in zip(ms, frames)]
        la = np.concatenate([loose(t)["area"] for t in tables])
        out, _ = track.link(tables, ms_, lr, mr, mp)
        rows = {}
        for r, rec in enumerate(out):
            for i, cx, cy in zip(rec["id"], rec["cx"], rec["cy"]):
                rows.setdefault(int(i), []).append((r, cx, cy))
        confirmed = {i: v for i, v in rows.items() if len(v) >= mr}
        x0, y0, x1, y1 = CLUSTER
        loose_ids = {i: v for i, v in confirmed.items()
                     if not np.mean([(x0 <= cx < x1) and (y0 <= cy < y1) for _, cx, cy in v]) > 0.5}
        gaps = [b - a - 1 for v in loose_ids.values() for (a, _, _), (b, _, _) in zip(v, v[1:]) if b - a > 1]
        print(f"\n== {name}: {op_ms:.2f} ms a row")
        print(f"mask regions a row {len(regions) / ROWS:.1f}: under {lo} px {np.mean(regions < lo) * len(regions) / ROWS:.1f}, "
              f"in bounds {np.mean((regions >= lo) & (regions <= hi)) * len(regions) / ROWS:.2f}, over {hi} px {np.mean(regions > hi) * len(regions) / ROWS:.2f}")
        print(f"loose records a row {len(la) / ROWS:.2f}: area {pct(la, (5, 25, 50, 95))} px; within 10% above min_area "
              f"{np.mean(la < lo * 1.1) * 100:.1f}%")
        print(f"ids {len(rows)} / confirmed {len(confirmed)} / loose confirmed {len(loose_ids)}; rows seen per loose id "
              f"{pct([len(v) for v in loose_ids.values()], (50, 95))}; loose gaps {len(gaps)}, rows lost in them {sum(gaps)}, "
              f"gap {pct(gaps, (50, 95, 100))}")


if __name__ == "__main__":
    main()
