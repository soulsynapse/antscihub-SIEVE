"""Series tool: ids across rows for a blob table, greedy nearest-neighbour; blobs in, tracks out.

`rows` is each table with an `id` column after its own, the plane kept; the signal is the tracks
seen in at least `min_rows` rows. `max_step` is px per row: a track unseen for g rows reaches g
times it and no further, so set it from one row's step, not from the distance an animal may cover
while lost. A track unseen over `lost_rows` ends and its id is not reused. Ids are assigned afresh
each run. With `merge_ratio` over 0, a track never continues onto a blob within reach whose area
is over that ratio of its own, the mean over its rows, or under its own over the ratio; a track
refused that way and taking nothing ends there, so a merged blob and the pieces it parts into are
new ids and a tracklet never spans a contact. At 0 area is not read.
"""
import numpy as np

from tools._draw import draw_tracks
from tools._table import OUTLINES, TRACKS_DTYPE as DTYPE, with_column

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "track", "series", "blobs", "tracks"
MAX_RATIO = 10.0
STEPS = 5           # recent steps averaged into the prediction
PARAMS = {
    "max_step": {"default": 4.0, "kind": "float", "range": (0.5, 200.0), "decimals": 1},
    "lost_rows": {"default": 30, "kind": "int", "range": (0, 600)},
    "min_rows": {"default": 3, "kind": "int", "range": (1, 60)},
    "min_p": {"default": 0.1, "kind": "float", "range": (0.0, 1.0)},
    "merge_ratio": {"default": 0.0, "kind": "float", "range": (0.0, MAX_RATIO), "decimals": 1},
    "outline": {"default": "box", "kind": "choice", "choices": OUTLINES},
}


class _Track:
    __slots__ = ("id", "pos", "steps", "seen", "hits", "area")

    def __init__(self, id, pos, row, area):
        self.id, self.pos, self.steps, self.seen, self.hits, self.area = id, pos, [], row, 1, area

    def predict(self, row, max_step):
        if not self.steps:
            return self.pos
        v = np.mean(self.steps[-STEPS:], axis=0)
        n = np.hypot(*v)
        if n > max_step:
            v *= max_step / n
        gap = row - self.seen
        return self.pos + v * sum(2.0 / (1 + k) for k in range(1, gap + 1))

    def take(self, pos, row, area):
        gap = row - self.seen
        self.steps.append((pos - self.pos) / gap)
        self.area = (self.area * self.hits + area) / (self.hits + 1)
        self.pos, self.seen, self.hits = pos, row, self.hits + 1


def _link_row(live, next_id, t, r, max_step, lost_rows, min_rows, min_p, merge_ratio):
    """Row `r`'s table linked onto `live`: the tracks still live after it, the next free id, the table
    with its ids and the count of tracks seen in it with at least `min_rows` hits."""
    t = np.asarray(t)
    rec = with_column(t, "id", np.full(len(t), -1, np.int32))
    live = [k for k in live if r - k.seen <= lost_rows]
    pos = np.stack([t["cx"], t["cy"]], axis=1).astype(np.float64) if len(t) else np.zeros((0, 2))
    area = t["area"].astype(np.float64) if len(t) else np.zeros(0)
    pairs, refused = [], set()
    for i, k in enumerate(live):
        gap = r - k.seen
        d = np.hypot(*(pos - k.predict(r, max_step)).T) / gap
        p = (1.0 / (1.0 + d / max_step) ** 2) * (1.0 - 0.75 * min(1.0, (gap - 1) / max(lost_rows, 1)))
        p[d > max_step] = 0
        if merge_ratio > 0:
            unfit = (area > merge_ratio * k.area) | (area < k.area / merge_ratio)
            if np.any(unfit & (d <= max_step)):
                refused.add(i)
            p[unfit] = 0
        pairs += [(p[j], i, j) for j in np.flatnonzero(p >= min_p)]
    pairs.sort(reverse=True)
    used_t, used_b = set(), set()
    for p, i, j in pairs:
        if i in used_t or j in used_b:
            continue
        used_t.add(i), used_b.add(j)
        live[i].take(pos[j], r, area[j])
        rec["id"][j] = live[i].id
    live = [k for i, k in enumerate(live) if i in used_t or i not in refused]
    for j in range(len(t)):
        if j not in used_b:
            live.append(_Track(next_id, pos[j], r, area[j]))
            rec["id"][j] = next_id
            next_id += 1
    return live, next_id, rec, sum(1 for k in live if k.seen == r and k.hits >= min_rows)


def link(tables, max_step, lost_rows, min_rows, min_p, merge_ratio=0.0):
    out, signal, live, next_id = [], np.zeros(len(tables), np.float32), [], 0
    for r, t in enumerate(tables):
        live, next_id, rec, signal[r] = _link_row(live, next_id, t, r, max_step, lost_rows, min_rows, min_p, merge_ratio)
        out.append(rec)
    rows = np.empty(len(out), object)
    rows[:] = out
    return rows, signal


def _knobs(params):
    return (float(params["max_step"]), int(params["lost_rows"]), int(params["min_rows"]), float(params["min_p"]),
            float(params["merge_ratio"]))


def run(series, params):
    rows, signal = link(series.data, *_knobs(params))
    return {"rows": rows, "signal": signal}


def step(state, row, i, params):
    live, next_id = ([], 0) if state is None else state
    live, next_id, rec, n = _link_row(live, next_id, row, i, *_knobs(params))
    return (live, next_id), {"rows": rec, "signal": np.float32(n)}


def draw(painter, row, result, start, params):
    draw_tracks(painter, row, result, start, params["outline"])


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import blobs, gray, threshold

    sys.exit(play([gray, threshold, blobs, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
