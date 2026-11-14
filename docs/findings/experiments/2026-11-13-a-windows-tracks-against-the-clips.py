"""Experiment behind docs/findings/2026-11-13-a-windows-tracks-against-the-clips.md, the observation the
Fork of Which results are the same result in docs/spec/held-results.md asks for: `track` stepped from a
window's first row against `track` stepped from the clip's, over the rows both reach, and `travel` and
`kinematics` over each.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-13-a-windows-tracks-against-the-clips.py [merge_ratio] 2>NUL

The document is video-tests/purb-168-178.json and its blobs tables are computed once; a walk of a range is
the tool stepped from state None at the range's first row with i counted from it, as worker._Walk.step
does it. A row is `relinked` where the window's ids do not map one to one onto the clip's as every row
before it had them: ids are numbered from the walk's first row, so the numbers always differ and the
linking is what is compared. `merge_ratio`, given, replaces the document's.
"""
import os
import sys

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from tools import kinematics, track, travel  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-168-178.json")
EVERY = 25


def stepped(tool, rows, params):
    state, shares = None, []
    for i, row in enumerate(rows):
        state, share = tool.step(state, row, i, params)
        shares.append(share)
    return shares


def relinked(clip, win):
    """The offsets at which the window's ids stop mapping one to one onto the clip's."""
    w2c, c2w, out = {}, {}, []
    for k, (c, w) in enumerate(zip(clip, win)):
        bad = False
        for cid, wid in zip(c["id"].tolist(), w["id"].tolist()):
            if w2c.get(wid, cid) != cid or c2w.get(cid, wid) != wid:
                bad = True
                c2w.pop(w2c.get(wid), None)
                w2c.pop(c2w.get(cid), None)
            w2c[wid], c2w[cid] = cid, wid
        if bad:
            out.append(k)
    return out


def differing(a, b):
    return np.flatnonzero(~np.isclose(np.asarray(a, np.float64), np.asarray(b, np.float64), equal_nan=True)).tolist()


def said(offsets):
    return f"{len(offsets):>4} {offsets[-1] if offsets else '-':>5}"


if __name__ == "__main__":
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    doc = D.load(DOC, tools)
    g = Graph(doc, Decoder(doc.video), tools)
    n = g.count
    blobs = [g.compute("blobs", r) for r in range(n)]
    p_track, p_travel = dict(g.entry("track").params), dict(g.entry("travel").params)
    if len(sys.argv) > 1:
        p_track["merge_ratio"] = float(sys.argv[1])
    p_kin = dict(kinematics.DEFAULTS)
    g.close()
    g.decoder.close()

    def chain(rows):
        t = stepped(track, rows, p_track)
        tables = [s["rows"] for s in t]
        return (tables, [s["signal"] for s in t], [s["signal"] for s in stepped(travel, tables, p_travel)],
                [s["signal"] for s in stepped(kinematics, tables, p_kin)])

    clip = chain(blobs)
    per = np.array([len(t) for t in blobs])
    print(f"{n} rows at {g.fps:.2f} fps; records a row {per.mean():.1f}, most {per.max()}; track {p_track}; travel {p_travel}; "
          f"kinematics {p_kin}; ids over the clip {max(int(t['id'].max()) for t in clip[0] if len(t)) + 1}")
    print("each pair is the rows that differ and the last of them, counted from the window's first row")
    print(f"{'window at':>9} {'rows':>5}   {'relinked':>10}   {'track':>10}   {'travel':>10}   {'kinematics':>10}")
    last = {"relinked": [], "track": [], "travel": [], "kinematics": []}
    for s in range(EVERY, n - EVERY, EVERY):
        win = chain(blobs[s:])
        found = {"relinked": relinked(clip[0][s:], win[0]), "track": differing(clip[1][s:], win[1]),
                 "travel": differing(clip[2][s:], win[2]), "kinematics": differing(clip[3][s:], win[3])}
        for name, offsets in found.items():
            last[name].append(offsets[-1] if offsets else -1)
        print(f"{s:>9} {n - s:>5}   " + "   ".join(said(found[name]) for name in last))
    print("the last differing row over every window, median and most: "
          + "; ".join(f"{name} {int(np.median(v))}, {max(v)}" for name, v in last.items()))
