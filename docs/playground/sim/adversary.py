"""Review experiments over the miniature's own machinery. Run: python -X utf8 exp.py A B C ..."""
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
WHICH = sys.argv[1:]
sys.argv = ["miniature.py", str(HERE.parents[2]), "0", "0"]
src = (HERE / "miniature.py").read_text(encoding="utf-8").split("\nfailed = False")[0]
G = {"__file__": str(HERE / "miniature.py"), "__name__": "mini"}
exec(compile(src, "miniature.py", "exec"), G)
globals().update({k: v for k, v in G.items() if not k.startswith("__")})


def make(name, nodes, bands=(), params=None, cuts=CHECKED):
    """nodes: (id, tool or None, src, input or None)."""
    folder = Path(SCRATCH) / name
    folder.mkdir()
    doc = D.Document(video=clip(folder / "v.avi", cuts))
    doc.add_node(D.VIDEO_TOOL)
    for nid, tool, s, into in nodes:
        if tool is not None:
            doc.add_node(tool, (0.0, 100.0 * len(doc.nodes)), None, nid)
        if s is not None:
            doc.connect(s, nid, *([into] if into else []))
    for b in bands:
        doc.node(b).band = (100.0, 255.0)
    for nid, ps in (params or {}).items():
        doc.node(nid).params.update(ps)
    D.save(doc, folder / "doc.json")
    win = window.PlayerWindow(str(folder / "doc.json"), "t", TOOLS)
    if win.playing:
        win.toggle_play()
    turned(win)
    settled(win)
    return win


def state(win, nodes, tag):
    p = win.graph.snapshot()
    for nid in nodes:
        e = p.entries[nid]
        rows = [c.extent.rows for c in e.cuts][:3]
        line = sorted({r for l in (win.plot.lines[nid].pieces if nid in win.plot.lines else []) for r in range(l.start, l.start + len(l.values))})
        print(f"  [{tag}] {nid}: fed={e.fed} key={e.key} cuts={len(e.cuts)} first={rows} standing={win.graph.standing(nid)!r} line_rows={len(line)}")


def sig(h, nid):
    return {k[1:]: float(np.nanmean(v)) for k, v in sorted(h.items(), key=str) if k[0] == nid}


GATED = lambda cutter: (("gray", "gray", D.VIDEO_TOOL, None), ("gate", "reduce", "gray", None), ("cutn", cutter, "gray", None),
                        ("cutn", None, "gate", "gate"), ("below", "reduce", "cutn", None))


def A():
    """A cutter in time whose run changes the frame: a param edit on it while runs are held."""
    win = make("A", GATED("gainpad"), ["gate"])
    win._toggle_clip(); settled(win)
    h1, k1 = holds(win), win._key("below")
    print("  gain=1 held below:", list(sig(h1, "below").items())[:2])
    win.doc.node("cutn").params["gain"] = 0
    win._params_changed("cutn"); settled(win)
    if not win._clip_asked:
        win._toggle_clip(); settled(win)
    h2, k2 = holds(win), win._key("below")
    print(f"  after gain=0 edit: below key moved={k1 != k2}; held below:", list(sig(h2, "below").items())[:2])
    win.set_window(0, 3 * PERIOD, by=HAND); settled(win)
    pcs = win.plot.lines["below"].pieces if "below" in win.plot.lines else []
    print("  line of below drawn after the edit, first values:", [float(v) for l in pcs[:1] for v in l.values[:4]])
    fresh = make("A2", GATED("gainpad"), ["gate"], {"cutn": {"gain": 0}})
    fresh._toggle_clip(); settled(fresh)
    h3 = holds(fresh)
    print("  fresh player at gain=0 held below:", list(sig(h3, "below").items())[:2], "key same as edited:", fresh._key("below") == k2)
    print("  edited player differs from fresh at", len(apart(h3, h2)), "of", len(h3), "held results")


def B():
    """A CUT_BY cutter with no PATHS and its gate unwired; and the gate unwired while runs are held."""
    win = make("B", GATED("pad")[:3] + GATED("pad")[4:], ["gate"])
    state(win, ["cutn", "below"], "never wired")
    win._toggle_clip(); settled(win)
    h = holds(win)
    print("  held of below after a clip walk:", [(k[1], k[2], len(v)) for k, v in h.items() if k[0] == "below"][:3])
    win = make("B2", GATED("pad"), ["gate"])
    win._toggle_clip(); settled(win)
    state(win, ["cutn", "below"], "wired, walked")
    win.doc.disconnect("cutn", "gate")
    win.sync(); settled(win)
    state(win, ["cutn", "below"], "gate unwired")
    win = make("B3", GATED("period"), ["gate"])
    win.doc.disconnect("cutn", "gate")
    win.sync(); settled(win)
    state(win, ["cutn", "below"], "period, gate unwired")


def C():
    """A gate fed a tracks result, which CUT_BY of period says it takes."""
    win = make("C", (("gray", "gray", D.VIDEO_TOOL, None), ("threshold", "threshold", "gray", None), ("detect", "detect", "threshold", None),
                     ("track", "track", "detect", None), ("cutn", "period", "gray", None), ("cutn", None, "track", "gate"),
                     ("below", "reduce", "cutn", None)))
    state(win, ["track", "cutn", "below"], "opened")
    win._toggle_clip(); settled(win)
    state(win, ["track", "cutn", "below"], "after a clip walk")
    r = win._clip_result("track")
    print("  track's result fields:", sorted(r) if isinstance(r, dict) else r)
    print("  held of below:", [(k[1], k[2], len(v)) for k, v in holds(win).items() if k[0] == "below"][:3])


def Dm():
    """The mark of other code on nodes below a cut in time."""
    win = opened("D")
    win._toggle_clip(); settled(win)
    reduce_ = BY_NAME["reduce"]
    on_disk = registry.code_print
    registry.code_print = lambda tool, seen=None: "other code" if tool is reduce_ else on_disk(tool, seen)
    try:
        marks = {}
        win.pane.set_stale = lambda nid, tip: marks.__setitem__(nid, bool(tip))
        win._show_stale()
        print("  reduce's code said changed; marked:", {n: marks.get(n) for n in ("gate", "gate2", "below", "smooth") if n in marks})
        print("  runs held of below under its key:", sum(1 for k in holds(win) if k[0] == "below"))
    finally:
        registry.code_print = on_disk


def E():
    """O11 of the cutter's own document: saved after a clip walk, copied, opened."""
    G["held"].File.write = WRITE
    win = opened("E")
    win._toggle_clip(); settled(win)
    win.save_document(); win._write_held(wait=True)
    want = holds(win)
    away = copied(Path(SCRATCH) / "E", "E-away")
    gray, ran = BY_NAME["gray"], []
    run = gray.run
    gray.run = lambda frames, row, params: (ran.append(row), run(frames, row, params))[1]
    try:
        got_win = player(away)
        got = holds(got_win)
        print(f"  first player held {len(want)}; the copy serves {len(got)} before a turn, apart {len(apart(want, got))}")
        turned(got_win); settled(got_win)
        got = holds(got_win)
        walked = sorted({r for r in ran if r != got_win.row})
        print(f"  after its turns: holds {len(got)}, apart {len(apart(want, got))}; gray ran at {len(walked)} rows besides the playhead's")
        p = got_win.graph.snapshot()
        print("  unheld:", sorted(p.unheld), "standing of", LOWEST, repr(got_win.graph.standing(LOWEST)), "below:", repr(got_win.graph.standing("below")))
    finally:
        gray.run = run


def F():
    """Three cuts in time, each under the last: the miniature's O8, O9, O10 over it."""
    g = G
    g["NESTED"], g["LOWEST"] = True, "inner3"
    g["BELOW"] = (("below", "reduce", "inner3"), ("smooth", "smooth", "below"))
    g["INNER"] = (("gate2", "reduce", "period", None), ("inner", "period", "period", None), ("inner", None, "gate2", "gate"),
                  ("gate3", "reduce", "inner", None), ("inner3", "period", "inner", None), ("inner3", None, "gate3", "gate"))
    doc0 = g["document"]

    def document(path, video):
        doc0(path, video)
        d = D.load(str(path)) if hasattr(D, "load") else None
        d.node("gate3").band = (100.0, 255.0)
        D.save(d, path)
        return str(path)
    g["document"] = document
    for name in ("bare_and_clip", "window_first", "window_shows"):
        try:
            said = g[name]()
        except Exception as e:
            said = [f"{type(e).__name__}: {e}"]
        print(f"  {name}: {'holds' if not said else 'fails'}", *[f"\n    {s}" for s in said[:8]])


def _three(tag):
    g = G
    for name in ("bare_and_clip", "window_first", "window_shows"):
        try:
            said = g[name]()
        except Exception as e:
            said = [f"{type(e).__name__}: {e}"]
        print(f"  {tag} {name}: {'holds' if not said else 'fails'}", *[f"\n    {s}" for s in said[:6]])


REGION = {"plate": [48, 64], "shapes": [{"name": "a", "polygon": [[8, 8], [40, 8], [40, 40], [8, 40]]}], "choice": "a", "serve clip": False}


def _region_doc(above):
    def document(path, video):
        doc = D.Document(video=video)
        doc.add_node(D.VIDEO_TOOL)
        order = ((("gray", "gray", D.VIDEO_TOOL, None), ("gate", "reduce", "gray", None), ("reg", "region", "gray", None),
                  ("period", "period", "reg", None), ("period", None, "gate", "gate"), ("below", "reduce", "period", None))
                 if above else
                 (("gray", "gray", D.VIDEO_TOOL, None), ("gate", "reduce", "gray", None), ("period", "period", "gray", None),
                  ("period", None, "gate", "gate"), ("reg", "region", "period", None), ("below", "reduce", "reg", None)))
        for nid, tool, s, into in (*order, ("smooth", "smooth", "below", None)):
            if tool is not None:
                doc.add_node(tool, (0.0, 100.0 * len(doc.nodes)), None, nid)
            doc.connect(s, nid, *([into] if into else []))
        doc.node("gate").band = (100.0, 255.0)
        doc.node("reg").params.update(REGION)
        D.save(doc, path)
        return str(path)
    return document


def R():
    """A region above a period, and below one: the miniature's O8, O9, O10 over each."""
    for above in (False,):
        G["document"] = _region_doc(above)
        tag = "region above the period:" if above else "region below the period:"
        win = opened(f"R{above}")
        state(win, ["reg", "period", "below"], tag)
        _three(tag)


def V():
    """Values a window draws before a clip walk and does not say best effort, against what the clip walk then holds."""
    win = opened("V")
    seen = []
    for name, s, n in WINDOWS[:3] + (("the first three periods", 0, 3 * PERIOD), ("mid-clip", CHECKED * PERIOD // 2 - 3, 3 * PERIOD)):
        win.set_window(s, n, by=HAND); settled(win)
        for nid, *_ in BELOW:
            for l in (win.plot.lines[nid].pieces if nid in win.plot.lines else []):
                seen += [(name, nid, l.start + i, float(v)) for i, v in enumerate(l.values) if s <= l.start + i < s + n and not l.best]
    win._toggle_clip(); settled(win)
    by = {}
    for (nid, cut, start), sg in holds(win).items():
        for i, v in enumerate(sg):
            by.setdefault((nid, start + i), []).append(float(v))
    same = lambda a, b: a == b or (a != a and b != b) or abs(a - b) < 1e-4
    bad = [(name, nid, r, v, by.get((nid, r))) for name, nid, r, v in seen if not any(same(v, w) for w in by.get((nid, r), []))]
    print(f"  {len(seen)} values drawn and not said best effort; {len(bad)} are not what the clip walk holds at that row")
    for b in bad[:8]:
        print("   ", b)


def H():
    """Steps of a save, a reopen, a param edit below the cuts and a band edit on the gate, with 100 and 400 cuts held."""
    G["held"].File.write = WRITE
    out = {}
    for cuts in (100, 400):
        win = opened(f"H{cuts}", cuts)
        win._toggle_clip(); settled(win)
        n = sum(run.cut is not None for run in win.runs)

        def save():
            win.save_document(); win._write_held(wait=True)

        def reopen():
            w2 = player(Path(SCRATCH) / f"H{cuts}"); turned(w2); settled(w2)

        def edit_below():
            win.doc.node("smooth").params["reach"] += 2; win._params_changed("smooth"); settled(win)

        def edit_gate():
            win.doc.node("gate").band = (101.0, 255.0); win._params_changed("gate"); settled(win)

        def scrub():
            win.goto(win.count // 2 + 3, commit=True); settled(win)

        out[cuts] = (n, *(sum(stepped(f).values()) for f in (save, reopen, scrub, edit_below, edit_gate)))
    for i, what in enumerate(("save", "reopen", "scrub", "edit below the cuts", "band edit on the gate"), 1):
        a, b = out[100][i], out[400][i]
        print(f"  {what}: {a} steps with {out[100][0]} cuts held, {b} with {out[400][0]}: {b / max(a, 1):.2f}x")


def H2():
    """Steps on the window's own thread, no worker turn taken, of one edit with 100 and 400 cuts held."""
    G["held"].File.write = WRITE
    out, top = {}, {}
    for cuts in (100, 400):
        win = opened(f"H{cuts}", cuts)
        win._toggle_clip(); settled(win)
        win.save_document(); win._write_held(wait=True)

        def save_again():
            win.save_document(); win._write_held(wait=True)

        def edit_below():
            win.doc.node("smooth").params["reach"] += 2; win._params_changed("smooth")

        def edit_below_once_more():
            win.doc.node("smooth").params["reach"] += 2; win._params_changed("smooth")

        def edit_gate():
            win.doc.node("gate").band = (101.0, 255.0); win._params_changed("gate")

        res = []
        for f in (save_again, edit_below, edit_below_once_more, edit_gate):
            st = stepped(f)
            res.append(sum(st.values()))
            top[(cuts, f.__name__)] = sorted(st.items(), key=lambda kv: -kv[1])[:4]
            settled(win)
        out[cuts] = res
    for i, what in enumerate(("save with nothing new", "edit below the cuts", "the same edit once more", "band edit on the gate")):
        a, b = out[100][i], out[400][i]
        print(f"  {what}: {a} steps with 100 cuts held, {b} with 400: {b / max(a, 1):.2f}x")
    for k in ((400, "edit_below"), (400, "edit_gate")):
        print("  most steps at", k, top[k])


def T():
    """Milliseconds on the window's own thread, no worker turn taken, of one edit below the cuts, the least of five, by cuts held."""
    import time
    G["held"].File.write = WRITE
    for cuts in (100, 400, 1600):
        win = opened(f"T{cuts}", cuts)
        win._toggle_clip(); settled(win)
        took = []
        for _ in range(5):
            at = time.perf_counter()
            win.doc.node("smooth").params["reach"] += 2; win._params_changed("smooth")
            took.append(1000 * (time.perf_counter() - at))
            settled(win)
        print(f"  {cuts} cuts held: {min(took):.1f} ms")
    import cProfile, pstats
    prof = cProfile.Profile()
    win.doc.node("smooth").params["reach"] += 2
    prof.runcall(win._params_changed, "smooth")
    rows = sorted(pstats.Stats(prof).stats.items(), key=lambda kv: -kv[1][3])
    for (file, line, fn), (_, calls, own, cum, _) in rows[:22]:
        if "sieve_player" in file:
            print(f"    {1000 * cum:7.1f} ms in all, {1000 * own:6.1f} its own, {calls:6d} calls: {Path(file).name}:{fn}")


def W():
    """Which functions' steps grow over a window moved, with 200 and 800 cuts held, and who makes the dataclasses made at 800."""
    import cProfile, pstats
    out = {}
    for cuts in (200, 800):
        win = opened(f"W{cuts}", cuts)
        win._toggle_clip(); settled(win)
        prof = cProfile.Profile()
        out[cuts] = stepped(lambda: (win.set_window(win.count // 2, win.window_[1], by=HAND), settled(win)), prof)
    print(f"  in all: {sum(out[200].values())} and {sum(out[800].values())}")
    for more, f in sorted(((n - out[200].get(f, 0), f) for f, n in out[800].items()), reverse=True)[:6]:
        print(f"    {more:7d} more steps, {out[200].get(f, 0)} to {out[800][f]}: {f}")
    for (file, line, fn), (_, calls, own, cum, callers) in pstats.Stats(prof).stats.items():
        if file == "<string>" and fn == "__init__":
            print(f"    {calls} calls of a dataclass's __init__, from", sorted(((n[0], Path(c[0]).name, c[2]) for c, n in callers.items()), reverse=True)[:5])


for name in WHICH:
    fn = globals()[name]
    print(f"== {name}: {fn.__doc__}  (cutter {CUTTER})")
    try:
        fn()
    except Exception:
        traceback.print_exc(limit=6, file=sys.stdout)
    sys.stdout.flush()
import os
os._exit(0)
