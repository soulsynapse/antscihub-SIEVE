"""Series tool: ids across rows for a blob table, greedy nearest-neighbour; blobs in, tracks out.

`rows` is each table with an `id` column after its own, the plane kept; the signal is the tracks
seen in at least `min_rows` rows. `max_step` is px per row: a track unseen for g rows reaches g
times it and no further, so set it from one row's step, not from the distance an animal may cover
while lost. A track unseen over `lost_rows` ends and its id is not reused. Ids are assigned afresh
each run.
"""
import numpy as np

from tools import blobs

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "track", "series", "blobs", "tracks"
DEFAULTS = {"max_step": 4.0, "lost_rows": 30, "min_rows": 3, "min_p": 0.1, "outline": "box"}
DTYPE = np.dtype(blobs.DTYPE.descr + [("id", np.int32)])      # the output's dtype for a table of blobs' own columns
STEPS = 5           # recent steps averaged into the prediction
TRAIL = 30          # rows of path drawn behind each box


def _with_id(t):
    return np.dtype(t.dtype.descr + [("id", np.int32)], metadata=dict(t.dtype.metadata or {}))


class _Track:
    __slots__ = ("id", "pos", "steps", "seen", "hits")

    def __init__(self, id, pos, row):
        self.id, self.pos, self.steps, self.seen, self.hits = id, pos, [], row, 1

    def predict(self, row, max_step):
        if not self.steps:
            return self.pos
        v = np.mean(self.steps[-STEPS:], axis=0)
        n = np.hypot(*v)
        if n > max_step:
            v *= max_step / n
        gap = row - self.seen
        return self.pos + v * sum(2.0 / (1 + k) for k in range(1, gap + 1))

    def take(self, pos, row):
        gap = row - self.seen
        self.steps.append((pos - self.pos) / gap)
        self.pos, self.seen, self.hits = pos, row, self.hits + 1


def link(tables, max_step, lost_rows, min_rows, min_p):
    out, signal, live, next_id = [], np.zeros(len(tables), np.float32), [], 0
    for r, t in enumerate(tables):
        t = np.asarray(t)
        rec = np.empty(len(t), _with_id(t))
        for name in t.dtype.names:
            rec[name] = t[name]
        rec["id"] = -1
        live = [k for k in live if r - k.seen <= lost_rows]
        pos = np.stack([t["cx"], t["cy"]], axis=1).astype(np.float64) if len(t) else np.zeros((0, 2))
        pairs = []
        for i, k in enumerate(live):
            gap = r - k.seen
            d = np.hypot(*(pos - k.predict(r, max_step)).T) / gap
            p = (1.0 / (1.0 + d / max_step) ** 2) * (1.0 - 0.75 * min(1.0, (gap - 1) / max(lost_rows, 1)))
            p[d > max_step] = 0
            pairs += [(p[j], i, j) for j in np.flatnonzero(p >= min_p)]
        pairs.sort(reverse=True)
        used_t, used_b = set(), set()
        for p, i, j in pairs:
            if i in used_t or j in used_b:
                continue
            used_t.add(i), used_b.add(j)
            live[i].take(pos[j], r)
            rec["id"][j] = live[i].id
        for j in range(len(t)):
            if j not in used_b:
                live.append(_Track(next_id, pos[j], r))
                rec["id"][j] = next_id
                next_id += 1
        signal[r] = sum(1 for k in live if k.seen == r and k.hits >= min_rows)
        out.append(rec)
    rows = np.empty(len(out), object)
    rows[:] = out
    return rows, signal


def run(series, params):
    rows, signal = link(series.data, float(params["max_step"]), int(params["lost_rows"]),
                        int(params["min_rows"]), float(params["min_p"]))
    return {"rows": rows, "signal": signal}


def draw(painter, row, result, start, params):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QPen

    if not isinstance(result, dict) or not 0 <= row - start < len(result["rows"]):
        return
    rows, i = result["rows"], row - start
    painter.setBrush(Qt.NoBrush)
    for b in rows[i]:
        pen = QPen(QColor.fromHsv(int(b["id"]) * 47 % 360, 200, 240), 0)
        pen.setCosmetic(True)
        painter.setPen(pen)
        blobs.outline(painter, b, params.get("outline", "box"))
        painter.drawText(QPointF(float(b["x"]), float(b["y"]) - 2), str(int(b["id"])))
        path = [(float(t["cx"][0]), float(t["cy"][0])) for t in (rows[k][rows[k]["id"] == b["id"]]
                                                                 for k in range(max(0, i - TRAIL), i + 1)) if len(t)]
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            painter.drawLine(QPointF(x0, y0), QPointF(x1, y1))


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_float("max_step", 0.5, 200.0, DEFAULTS["max_step"], decimals=1)
    w.add_int("lost_rows", 0, 600, DEFAULTS["lost_rows"])
    w.add_int("min_rows", 1, 60, DEFAULTS["min_rows"])
    w.add_float("min_p", 0.0, 1.0, DEFAULTS["min_p"])
    w.add_choice("outline", blobs.OUTLINES, DEFAULTS["outline"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray, threshold

    sys.exit(play([gray, threshold, blobs, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
