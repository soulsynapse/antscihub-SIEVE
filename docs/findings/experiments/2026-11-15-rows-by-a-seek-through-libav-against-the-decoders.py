"""One-off: whether libav asked directly, through PyAV, hands out by a seek the row sieve_player's
Decoder hands out in order, and what each takes. PyAV is no requirement of the player: install it
somewhere and put that on PYTHONPATH. Three parts, each said on a line. The packets' times read with
no frame decoded, against decoder.frame_times: the count and the seconds of each. The first ROWS
rows in order through libav, with the place of each one's pts among the packets', against the
Decoder's luma plane of the same row: how many are another plane, and a step's ms on each. Then
every one of them from the last to the first through libav, each a seek to the row's pts and frames
decoded until that pts comes, a seek whose first frame out is past the row asked again further
back, against the same rows on a Decoder holding one frame: how many are another row, how many no
seek got behind, the seeks and how many landed past, and the ms a row took on each. The Decoder's
decodes are not said beside libav's: the plugin's own, inside a seek, are not counted by it. Stops at BUDGET seconds and says how far it got. Run
from the repo root:
python docs/findings/experiments/2026-11-15-rows-by-a-seek-through-libav-against-the-decoders.py <video> [rows]"""
import os
import sys
import time

import av
import numpy as np

sys.path.insert(0, os.getcwd())

from sieve_player import decoder  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402

path = sys.argv[1]
ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 120
BUDGET = 45.0
began = time.perf_counter()
decoder.QUIET = True    # the Decoder's luma is then the stream's plane, as libav's is


def plane(frame):
    p = frame.planes[0]
    return np.frombuffer(p, np.uint8).reshape(p.height, p.line_size)[::4, :p.width:4].copy()


t = time.perf_counter()
with av.open(path) as c:
    pts = np.sort(np.array([p.pts for p in c.demux(video=0) if p.pts is not None], np.int64))
libav_table = time.perf_counter() - t
t = time.perf_counter()
times = decoder.frame_times(path)
cv2_table = time.perf_counter() - t
print(f"{path}: {len(pts)} packet times through libav in {libav_table:.2f} s, {len(set(pts.tolist()))} distinct; "
      f"{len(times)} through the plugin in {cv2_table:.2f} s")

d = Decoder(path)
d.output = "luma"
theirs = [d.read(r)[::4, ::4].copy() for r in range(ROWS)]
step_cv2 = d.step_ms
d.close()

c = av.open(path)
s = c.streams.video[0]
s.thread_type = "AUTO"
t, ours, at = time.perf_counter(), [], []
for f in c.decode(s):
    at.append(f.pts)
    ours.append(plane(f))
    if len(ours) == ROWS:
        break
step_libav = (time.perf_counter() - t) * 1000 / ROWS
places = [int(np.searchsorted(pts, x)) for x in at]
other = [r for r in range(ROWS) if ours[r].shape != theirs[r].shape or not np.array_equal(ours[r], theirs[r])]
print(f"  in order: the first frame out is packet {places[0]} by its pts, the rest "
      f"{'each the next' if places == list(range(places[0], places[0] + ROWS)) else places}; "
      f"{len(other)} of {ROWS} planes another than the Decoder's {other[:12] or ''}; "
      f"a step {step_libav:.1f} ms through libav, {step_cv2:.1f} ms on the Decoder")

asks = past = decodes = 0


def by_a_seek(want):
    """The frame whose pts is `want`: a seek to it, and where the first frame out is past it, a seek
    further back, twice as far each time, the last of them to before the stream's first packet."""
    global asks, past, decodes
    place, back = int(np.searchsorted(pts, want)), 0
    while True:
        k = place - back
        c.seek(int(pts[k]) if k >= 0 else int(2 * pts[0] - pts[1]), stream=s, backward=True)
        asks += 1
        first = True
        for f in c.decode(s):
            decodes += 1
            if first and f.pts > want:
                past += 1
                break
            first = False
            if f.pts >= want:
                return f
        if k < 0:
            return None
        back = 2 * back or 1


off, unreached, read = {}, [], 0
t = time.perf_counter()
for r in reversed(range(ROWS)):
    if time.perf_counter() - began > BUDGET * 0.55:
        break
    got = by_a_seek(at[r])
    read += 1
    if got is None:
        unreached.append(r)
    elif not np.array_equal(plane(got), ours[r]):
        off[r] = [k for k, g in enumerate(ours) if np.array_equal(plane(got), g)] or "no row"
row_libav = (time.perf_counter() - t) * 1000 / max(read, 1)
c.close()

d = Decoder(path, cache_bytes=1)
d.output = "luma"
d.read(ROWS + 40)
d.seeks, t = 0, time.perf_counter()
their_off, their_read = 0, 0
for r in reversed(range(ROWS)):
    if time.perf_counter() - began > BUDGET:
        break
    their_off += not np.array_equal(d.read(r)[::4, ::4], theirs[r])
    their_read += 1
row_cv2 = (time.perf_counter() - t) * 1000 / max(their_read, 1)
print(f"  by a seek: {read} rows through libav, {len(off)} another row than in order {off or ''}, {len(unreached)} no seek "
      f"got behind {unreached or ''}, {asks} seeks of which {past} landed past the row asked, {decodes} decodes, "
      f"{row_libav:.1f} ms a row; {their_read} on the Decoder, {their_off} another row, {d.seeks} seeks, "
      f"{row_cv2:.1f} ms a row; {time.perf_counter() - began:.0f} s")
d.close()
