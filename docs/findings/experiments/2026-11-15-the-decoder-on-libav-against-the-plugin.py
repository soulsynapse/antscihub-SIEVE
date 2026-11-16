"""One-off: whether sieve_player's Decoder, on libav, hands out what cv2's FFmpeg plugin hands out
of the same file, and what each takes. Said: the size, frame rate and count each claims; of the
first ROWS rows in order, how many of the Decoder's bgr are other values than the plugin's BGR, and
of its luma than the plugin's unconverted plane where that is a plane; a row's ms in order on each,
bgr; then each of those rows from the last to the first on a Decoder holding one frame, so each
read is a seek, how many are another row than in order, the ms a row took, and whether the file's
seeks were left numbered. Stops at BUDGET seconds and says how far it got. Run from the repo root:
python docs/findings/experiments/2026-11-15-the-decoder-on-libav-against-the-plugin.py <video> [rows]"""
import os
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.getcwd())

from sieve_player.decoder import Decoder  # noqa: E402

path = sys.argv[1]
ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 120
BUDGET = 45.0
began = time.perf_counter()

d = Decoder(path)
cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG)
theirs = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
ours = d.width, d.height, d.fps, d.count
print(f"{path}: the Decoder claims {ours}, the plugin {theirs}{'' if ours[:2] == theirs[:2] and ours[3] == theirs[3] and abs(ours[2] - theirs[2]) < 1e-9 else ', ANOTHER'}")

t, plugin_bgr = time.perf_counter(), []
for r in range(ROWS):
    ok, f = cap.read()
    plugin_bgr.append(f)
plugin_ms = (time.perf_counter() - t) * 1000 / ROWS
cap.release()
t = time.perf_counter()
in_order = [d.read(r) for r in range(ROWS)]
decoder_ms = (time.perf_counter() - t) * 1000 / ROWS
other = [r for r in range(ROWS) if in_order[r].shape != plugin_bgr[r].shape or not np.array_equal(in_order[r], plugin_bgr[r])]
worst = max((int(np.abs(in_order[r].astype(int) - plugin_bgr[r]).max()) for r in other if in_order[r].shape == plugin_bgr[r].shape), default=0)
print(f"  bgr in order: {len(other)} of {ROWS} rows other values than the plugin's {other[:8] or ''}{f', {worst} apart at most' if other else ''}; "
      f"a row {decoder_ms:.2f} ms on the Decoder, {plugin_ms:.2f} ms on the plugin")
del plugin_bgr

cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG)
cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
d.output = "luma"
n = min(ROWS, 30)
planes = [cap.read()[1] for _ in range(n)]
cap.release()
if planes[0].ndim == 2 and planes[0].shape == (d.height, d.width):
    off = sum(not np.array_equal(d.read(r), planes[r]) for r in range(n))
    print(f"  luma in order: {off} of {n} rows other values than the plugin's unconverted plane; the plane {'read' if d.luma else 'converted'}, limited range {d.limited}")
else:
    print(f"  luma: the plugin's unconverted frame is no plane of the frame's size, {planes[0].shape}; the Decoder's luma is {'the plane' if d.luma else 'converted from bgr'}")
d.close()
small = [f[::4, ::4].copy() for f in in_order]
del in_order, planes

d = Decoder(path, cache_bytes=1)
d.read(ROWS + 40)
d.seeks, t = 0, time.perf_counter()
off, read = {}, 0
for r in reversed(range(ROWS)):
    if time.perf_counter() - began > BUDGET:
        break
    f = d.read(r)[::4, ::4]
    read += 1
    if not np.array_equal(f, small[r]):
        off[r] = [k for k, g in enumerate(small) if np.array_equal(f, g)] or "no row"
print(f"  by a seek: {read} of {ROWS} rows, {len(off)} another row than in order {off or ''}; {d.seeks} seeks, "
      f"{(time.perf_counter() - t) * 1000 / max(read, 1):.1f} ms a row; seeks {'NOT ' if d._counts_only else ''}numbered; {time.perf_counter() - began:.0f} s")
d.close()
