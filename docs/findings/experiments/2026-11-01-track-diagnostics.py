"""Experiment behind docs/findings/2026-11-01-track-diagnostics.md: what the linker's own evidence
says about the ids it hands out, on a document's settings, with no ground truth.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-01-track-diagnostics.py [document] [start] [rows] [events.csv]

Reads the video, threshold, blobs and track params from the document (default
video-tests/purb-settings.json), decodes the rows once, runs the blobs tool as the GUI would, then
links with a copy of tools/track.link that logs each event with its row, id and position: contested
assignments, reacquisitions with the gap and the distance jumped, absorptions, births beside a blob
of the row before (the split half of a merge) and elsewhere, deaths. The copy's ids are asserted
equal to the tool's, so the first pass measures the tool; the reach of a lost track is then varied
(sqrt of the gap, flat, a sixth of the lost rows) to read the rule's share of the jumps. Events of
the first pass go to a csv of row, kind, id, x, y, so a row can be scrubbed to in the GUI.
"""
import csv
import json
import os
import sys
import time

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from sieve_player import Decoder  # noqa: E402
from tools import blobs, track  # noqa: E402

DOC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "video-tests", "purb-settings.json")
START = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
ROWS = int(sys.argv[3]) if len(sys.argv) > 3 else 600
EVENTS = sys.argv[4] if len(sys.argv) > 4 else None
NEAR = 2.0             # a birth within this many max_steps of a blob last row is a split
CONTEST = 0.5          # a rival pair with this share of the winner's p makes the take contested


def params(doc, tool):
    return next(n["params"] for n in doc["nodes"] if n["tool"] == tool)


def pct(a, q=(50, 95, 100)):
    a = np.asarray(a, np.float64)
    if len(a) == 0:
        return "none"
    return "  ".join(f"p{p} {np.percentile(a, p):.1f}" for p in q)


def link(tables, max_step, lost_rows, min_rows, min_p, reach):
    """tools/track.link with the gate `d / reach(gap) <= max_step` and an event log; reach(gap) == gap
    is the tool's rule."""
    out, live, next_id, events = [], [], 0, []
    n_contested = n_pairs = 0
    for r, t in enumerate(tables):
        rec = np.empty(len(t), track._with_id(t))
        for name in t.dtype.names:
            rec[name] = t[name]
        rec["id"] = -1
        for k in live:
            if r - k.seen > lost_rows:
                events.append((r, "death", k.id, k.pos[0], k.pos[1], 0, r - k.seen))
        live = [k for k in live if r - k.seen <= lost_rows]
        pos = np.stack([t["cx"], t["cy"]], axis=1).astype(np.float64) if len(t) else np.zeros((0, 2))
        pairs, dist = [], {}
        for i, k in enumerate(live):
            gap = r - k.seen
            raw = np.hypot(*(pos - k.predict(r, max_step)).T)
            d = raw / reach(gap)
            p = (1.0 / (1.0 + d / max_step) ** 2) * (1.0 - 0.75 * min(1.0, (gap - 1) / max(lost_rows, 1)))
            p[d > max_step] = 0
            for j in np.flatnonzero(p >= min_p):
                pairs.append((p[j], i, j))
                dist[i, j] = raw[j]
        pairs.sort(reverse=True)
        used_t, used_b = set(), set()
        for p, i, j in pairs:
            if i in used_t or j in used_b:
                continue
            rivals = [q for q, a, b in pairs if (a == i) != (b == j) and a not in used_t and b not in used_b]
            n_pairs += 1
            if rivals and max(rivals) >= CONTEST * p:
                n_contested += 1
                events.append((r, "contested", live[i].id, pos[j][0], pos[j][1], max(rivals) / p, 0))
            used_t.add(i), used_b.add(j)
            gap = r - live[i].seen
            if gap > 1:
                events.append((r, "reacquire", live[i].id, pos[j][0], pos[j][1], gap, dist[i, j]))
            live[i].take(pos[j], r)
            rec["id"][j] = live[i].id
        for i, k in enumerate(live):
            if i in used_t or k.seen != r - 1:
                continue
            q = k.predict(r, max_step)
            for j in used_b:
                b = t[j]
                if b["x"] <= q[0] < b["x"] + b["w"] and b["y"] <= q[1] < b["y"] + b["h"]:
                    events.append((r, "absorbed", k.id, q[0], q[1], rec["id"][j], 0))
                    break
        prev = tables[r - 1] if r else t[:0]
        for j in range(len(t)):
            if j not in used_b:
                near = len(prev) and np.hypot(prev["cx"] - pos[j][0], prev["cy"] - pos[j][1]).min() <= NEAR * max_step
                events.append((r, "split" if near else "birth", next_id, pos[j][0], pos[j][1], 0, 0))
                live.append(track._Track(next_id, pos[j], r))
                rec["id"][j] = next_id
                next_id += 1
        out.append(rec)
    return out, events, next_id, n_contested, n_pairs


def report(name, out, events, n_ids, n_contested, n_pairs, max_step, min_rows):
    kinds = {}
    for e in events:
        kinds.setdefault(e[1], []).append(e)
    hits = np.zeros(n_ids, int)
    first, last = np.full(n_ids, len(out)), np.zeros(n_ids, int)
    for r, rec in enumerate(out):
        for i in rec["id"]:
            hits[i] += 1
            first[i], last[i] = min(first[i], r), max(last[i], r)
    span = last - first + 1
    confirmed = hits >= min_rows
    steps = []
    for a, b in zip(out, out[1:]):
        for i in np.intersect1d(a["id"], b["id"]):
            pa, pb = a[a["id"] == i][0], b[b["id"] == i][0]
            steps.append(np.hypot(pb["cx"] - pa["cx"], pb["cy"] - pa["cy"]))
    re = kinds.get("reacquire", [])
    print(f"\n== {name}")
    print(f"ids {n_ids}, confirmed (>= {min_rows} rows) {confirmed.sum()}; rows seen per confirmed id {pct(hits[confirmed])}; "
          f"span {pct(span[confirmed])}; seen/span {np.median(hits[confirmed] / span[confirmed]):.2f} median")
    print(f"assignments {n_pairs}, contested (rival p >= {CONTEST} of winner) {n_contested} = {100 * n_contested / max(n_pairs, 1):.1f}%")
    print(f"consecutive-row steps: {pct(steps)} px, over max_step {np.mean(np.asarray(steps) > max_step) * 100:.1f}%")
    print(f"reacquisitions {len(re)}: gap {pct([e[5] for e in re])} rows; jump {pct([e[6] for e in re])} px; "
          f"jumps over 2*max_step {sum(e[6] > 2 * max_step for e in re)}, over 10*max_step {sum(e[6] > 10 * max_step for e in re)}")
    print(f"absorbed (merge half) {len(kinds.get('absorbed', []))}; births beside a blob (split half) {len(kinds.get('split', []))}; "
          f"births elsewhere {len(kinds.get('birth', []))}; deaths {len(kinds.get('death', []))}")


def main():
    doc = json.load(open(DOC, encoding="utf-8"))
    v, th, bp, tp = params(doc, "video"), params(doc, "threshold"), params(doc, "blobs"), params(doc, "track")
    dec = Decoder(doc["video"])
    dec.output, dec.scale = v.get("output", "luma"), float(v.get("scale", 1.0))
    print(f"{doc['video']}: {dec.width}x{dec.height} @ {dec.fps:.2f} fps; rows {START}..{START + ROWS - 1} at {dec.scale}; "
          f"threshold {th}; blobs {bp}; track {tp}")
    t0 = time.perf_counter()
    frames = [dec.read(r) for r in range(START, START + ROWS)]
    dec.close()
    flag = cv2.THRESH_BINARY_INV if th.get("invert") else cv2.THRESH_BINARY
    tables = [blobs.find(cv2.threshold(f, int(th["thresh"]), 255, flag)[1], int(bp["min_area"]), int(bp["max_area"]),
                         255 - f, int(bp["core_threshold"]), bool(bp["split"])) for f in frames]
    print(f"decode + detect {time.perf_counter() - t0:.1f} s; blobs a row {pct([len(t) for t in tables], (5, 50, 95))}; "
          f"area {pct(np.concatenate([t['area'] for t in tables]), (5, 50, 95))} px")
    ms, lr, mr, mp = float(tp["max_step"]), int(tp["lost_rows"]), int(tp["min_rows"]), float(tp["min_p"])
    out, events, n_ids, nc, npair = link(tables, ms, lr, mr, mp, lambda g: g)
    ref, _ = track.link(tables, ms, lr, mr, mp)
    assert all(np.array_equal(a["id"], b["id"]) for a, b in zip(out, ref)), "the copy drifted from tools/track.link"
    report(f"tools/track.link: reach = gap * max_step, lost_rows {lr}", out, events, n_ids, nc, npair, ms, mr)
    for name, reach, lost in (("reach = sqrt(gap) * max_step", np.sqrt, lr),
                              ("reach = max_step, flat", lambda g: 1, lr),
                              (f"reach = gap * max_step, lost_rows {lr // 6}", lambda g: g, lr // 6)):
        o, e, n, c, p = link(tables, ms, lost, mr, mp, reach)
        report(name, o, e, n, c, p, ms, mr)
    if EVENTS:
        with open(EVENTS, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(("row", "kind", "id", "x", "y", "a", "b"))
            for e in events:
                w.writerow((e[0] + START, e[1], e[2], f"{e[3]:.1f}", f"{e[4]:.1f}", f"{e[5]:.2f}", f"{e[6]:.2f}"))
        print(f"\nevents of the tool's own pass: {EVENTS} (a: gap, rival ratio or absorber id; b: jump px or rows lost)")


if __name__ == "__main__":
    main()
