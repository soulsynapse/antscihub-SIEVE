"""`python -m sieve_player.bare job.json`: the clip walked in a process of its own, with no stream
listened to and no interface beside it, and the series chain's results left in a file. The window
starts it (PlayerWindow's Bare) and reads its stdout, one JSON object a line: `{"done", "total",
"rate"}` as rows land, `{"count"}` where the stream ended short of the rows claimed, then one of `{"results": path}`, `{"refused": why}` or `{"failed": [row,
node, text]}`. The job is `job()`'s dict. The walk is walk._Walk's own, driven on this thread, on a
Graph handed a result_keeper.Keeper: a frame node's small rows made here are read back by the
next bare walk of the same document, code and footage instead of made again.
"""
import json
import os
import pickle
import sys
import time

from . import budget

TELL = 0.1      # s between the lines that say how far the walk is
HOLD = budget.here()["hold"] # what the memo and the plate's cache may each hold: nothing reads a row again but a tool reading near its own


def job(doc, video, tools, out):
    """What a bare walk is started with: the document as it stands, where it lives, the video the
    player has open, the tools by the folders their files are in and the file the results go to."""
    files = [os.path.abspath(t.__file__) for t in tools.values() if getattr(t, "__file__", None)]
    return {"document": doc.to_dict(), "path": doc.path, "video": video,
            "roots": sorted({os.path.dirname(f) for f in files}), "out": out}


class _Told:
    """A signal's place on a _Walk: what was last emitted, and a call for each."""

    def __init__(self, then=None):
        self.last, self.then = None, then

    def emit(self, *args):
        self.last = args
        if self.then is not None:
            self.then(*args)


def say(**line):
    print(json.dumps(line), flush=True)


def main(path):
    with open(path, encoding="utf-8") as f:
        j = json.load(f)
    for root in j["roots"]:
        sys.path.insert(0, os.path.dirname(root))
    from .decoder import Decoder, EndOfStream
    from .document import Document
    from .graph import Graph
    from .registry import discover
    from .result_keeper import Keeper
    from .walk import _Walk

    tools = {e.name: e.module for e in discover(*j["roots"]) if e.ok}
    doc = Document.from_dict(j["document"], tools)
    doc.path = j["path"]
    keeper = Keeper(j["video"])
    g = Graph(doc, Decoder(j["video"], cache_bytes=HOLD), tools, memo_bytes=HOLD, keeper=keeper)
    g.sync()
    p = g.snapshot()
    if not g.fed(p.walk):
        say(refused="nothing reaches a walked node")
        return 1
    t0 = [None]

    def told(done, total, *was):
        t0[0] = t0[0] or (time.perf_counter(), done)
        dt = time.perf_counter() - t0[0][0]
        say(done=done, total=total, rate=(done - t0[0][1]) / dt if dt > 0 else 0.0)

    ready, refused, failed = _Told(), _Told(), _Told()
    walk = _Walk(g, name="clip", every=g.count, progress=_Told(told), ready=ready, refused=refused, failed=failed, tell_every=TELL, plan=p)
    walk.begin(0, g.count)
    try:
        while walk.i < walk.length:
            walk.turn()
    except EndOfStream:     # as the Worker takes it: the walk closes at the rows it has
        say(count=g.count)
        walk.ended()
        if failed.last:
            say(failed=[failed.last[0], failed.last[1], "the chain raised over the rows the stream had"])
            return 1
    except Exception as e:
        say(failed=[walk.start + walk.i, getattr(e, "sieve_node", ""), f"{type(e).__name__}: {e}"])
        return 1
    finally:
        keeper.close()
    if refused.last:
        say(refused=refused.last[0])
        return 1
    results, start, fps = ready.last or ({}, 0, g.fps)
    with open(j["out"], "wb") as f:
        pickle.dump((results, start, fps), f, protocol=pickle.HIGHEST_PROTOCOL)
    say(results=j["out"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
