"""One-off: whether row r of a clip cut by tools/_cutfile.py's ffmpeg command is row r of the plate,
cut to the rect, as sieve_player's Decoder reads both. One shape of a geometry file is cut at each
quality; every row is read in order and compared with the plate's, then sampled rows are read by a
seek on fresh decoders and matched against the plate's rows two either side; last, each of the
plate's first OWN rows, and the lossless clip's, is read by a seek and compared with the same file's
read in order. With `rows`, only that many are cut from the video's start, which leaves its end
unread. Run from the repo root; the work folder is deleted and made again:
python docs/findings/experiments/2026-11-15-a-cut-clips-rows-against-the-plates.py <work folder> <video> <geometry.json> [rows]"""
import os
import random
import shutil
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.getcwd())

from sieve_player.decoder import Decoder, EndOfStream  # noqa: E402
from tools import _cutfile as C  # noqa: E402
from tools import region  # noqa: E402

work, video, geometry = (os.path.abspath(p) for p in sys.argv[1:4])
rows = int(sys.argv[4]) if len(sys.argv) > 4 else None
SEEKS, EITHER_SIDE, OWN = 20, 2, 120
shutil.rmtree(work, ignore_errors=True)
os.makedirs(work)
params = region.load_geometry(geometry)
name, (y0, y1, x0, x1) = region.crops(params)[0]
print(f"{os.path.basename(video)}: {name} at y {y0}-{y1}, x {x0}-{x1}" + (f", the first {rows} rows" if rows else ""))


def differ(a, b):
    return float(np.mean(np.abs(a.astype(np.int16) - b.astype(np.int16))))


for quality in C.QUALITIES:
    clip = os.path.join(work, f"{quality}.mp4")
    argv = C.command(video, [(clip, (y0, y1, x0, x1))], quality)
    if rows:
        argv[argv.index(clip):argv.index(clip)] = ["-frames:v", str(rows)]
    t = time.perf_counter()
    subprocess.run(argv, check=True)
    spent = time.perf_counter() - t
    plate, cut = Decoder(video), Decoder(clip)
    n, worst, unequal, in_order = 0, 0.0, 0, {"plate": [], "clip": []}
    try:
        while rows is None or n < rows:
            a, b = cut.read(n), plate.read(n)[y0:y1, x0:x1]
            d = differ(a, b)
            if quality == C.QUALITIES[0] and n < OWN:
                in_order["plate"].append(b.copy()), in_order["clip"].append(a.copy())
            worst, unequal, n = max(worst, d), unequal + (not np.array_equal(a, b)), n + 1
    except EndOfStream:
        pass
    ends = "unread" if rows else (cut.count, plate.count)
    plate.close(), cut.close()
    random.seed(0)
    sample = sorted({0, 1, 2, n - 3, n - 2, n - 1, *random.sample(range(n), SEEKS)})
    off = {}
    for r in reversed(sample):      # backward, so every read is a seek
        plate, cut = Decoder(video), Decoder(clip)
        a = cut.read(r)
        near = {d: differ(a, plate.read(r + d)[y0:y1, x0:x1]) for d in range(-EITHER_SIDE, EITHER_SIDE + 1) if 0 <= r + d < n}
        best = min(near, key=near.get)
        if best != 0:
            off[r] = (best, near)
        plate.close(), cut.close()
    print(f"  {quality}: cut in {spent:.1f} s; {n} rows read in order, {unequal} not equal to the plate's, mean abs difference "
          f"at worst {worst:.3f}; counts at the end (clip, plate) {ends}; {len(sample)} rows by a seek, "
          f"{len(off)} nearest to another plate row than their own {off or ''}")
    for what, path in (("plate", video), ("clip", clip)):
        off = {}
        for r in reversed(range(len(in_order[what]))):
            d = Decoder(path)
            f = d.read(r) if what == "clip" else d.read(r)[y0:y1, x0:x1]
            d.close()
            if not np.array_equal(f, in_order[what][r]):
                off[r] = [k for k, g in enumerate(in_order[what]) if np.array_equal(f, g)] or "no row"
        if in_order[what]:
            print(f"  the {what}'s first {len(in_order[what])} rows by a seek against its own in order: {len(off)} differ, "
                  f"each the in-order row {off or ''}")
