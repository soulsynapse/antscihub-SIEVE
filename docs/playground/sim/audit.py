"""What each act of the player costs against each size that can grow, as docs/playground/JOURNAL.md
plans it: one size varied with the others at BASE, every act taken on one player a size, the steps
of the act alone and of the worker's turns after it counted, and the slope of log steps on log
size set against EXPECTED. Run: python -X utf8 audit.py [size ...], MINIATURE_CUTTER as the
miniature takes it. It prints a table and the functions a finding's growth is of.
"""
import faulthandler
import math
import sys
from pathlib import Path

faulthandler.dump_traceback_later(1500, exit=True)     # a run that hangs says where and ends

HERE = Path(__file__).resolve().parent
ASKED = sys.argv[1:]
sys.argv = ["miniature.py", str(HERE.parents[2]), "0", "0"]
G = {"__file__": str(HERE / "miniature.py"), "__name__": "mini"}
exec(compile((HERE / "miniature.py").read_text(encoding="utf-8").split("\nfailed = False")[0], "miniature.py", "exec"), G)
G["held"].File.write = G["WRITE"]
opened, settled, stepped, player, HAND = (G[n] for n in ("opened", "settled", "stepped", "player", "HAND"))

SIZES = {"cuts": (50, 100, 200, 400), "rows a cut": (4, 8, 16), "window": (1, 2, 4), "chain": (0, 2, 6)}
BASE = {"cuts": 100, "rows a cut": 4, "window": 1, "chain": 0}
OVER, NOISE = 0.25, 2000
WINDOW_CUTS = 3     # the window holds this many cuts at size 1, so its length is in cuts and the longest, lengthened, ends inside the shortest clip

ALL, SHOWN, CHAIN = {"cuts": 1, "rows a cut": 1, "chain": 1}, {"window": 1, "rows a cut": 1, "chain": 1}, {"chain": 1}
AGAIN = {**ALL, "window": 1}     # what an edit makes stale is walked again, the window with it
EXPECTED = {    # act -> (the sizes its steps at once may grow with, and until settled), each to its exponent; a size unnamed is 0
    "window moved, none held": (SHOWN, SHOWN),
    "clip walk": ({}, ALL),
    "scrub": (CHAIN, CHAIN),
    "window moved, cuts held": (SHOWN, SHOWN),
    "window lengthened, cuts held": (SHOWN, SHOWN),
    "marks of other code": (CHAIN, {}),
    "save": (ALL, {}),
    "reopen": (ALL, SHOWN),
    "param edited below the cuts": (SHOWN, AGAIN),
    "gate's band edited": (SHOWN, AGAIN),
    "let go": (CHAIN, AGAIN),
}


def measured(tag, size):
    """act -> (function -> its steps at once, function -> its steps until settled) on a player of `size`."""
    G["KEPT"], G["PERIOD"] = size["rows a cut"], 2 * size["rows a cut"]
    more = [(f"more{i}", "smooth", "smooth" if i == 0 else f"more{i - 1}") for i in range(size["chain"])]
    G["BELOW"] = (("below", "reduce", G["LOWEST"]), ("smooth", "smooth", "below"), *more)
    win = opened(tag, size["cuts"])
    n = size["window"] * WINDOW_CUTS * G["PERIOD"]
    win.set_window(0, n, by=HAND)
    settled(win)
    out, mid = {}, size["cuts"] // 2 * G["PERIOD"]
    assert mid + 2 * n <= win.count, "the window lengthened runs off the clip, and the cell would measure the clip's end"

    def act(name, do, then=None):
        got = []
        at_once = stepped(lambda: got.append(do()))
        out[name] = (at_once, stepped(lambda: settled(then(got[0]) if then else win)))

    def edit_below():
        win.doc.node("smooth").params["reach"] += 2
        win._params_changed("smooth")

    def edit_band():
        win.doc.node("gate").band = (101.0, 255.0)
        win._params_changed("gate")

    def save():
        win.save_document()
        win._write_held(wait=True)

    act("window moved, none held", lambda: win.set_window(mid, n, by=HAND))
    win.set_window(0, n, by=HAND)
    settled(win)
    act("clip walk", win._toggle_clip)
    act("scrub", lambda: win.goto(mid + 3, commit=True))
    act("window moved, cuts held", lambda: win.set_window(mid, n, by=HAND))
    act("window lengthened, cuts held", lambda: win.set_window(mid, 2 * n, by=HAND))
    win.set_window(mid, n, by=HAND)
    settled(win)
    act("marks of other code", win._show_stale)
    act("save", save)
    act("reopen", lambda: player(Path(G["SCRATCH"]) / tag), then=lambda other: other)
    act("param edited below the cuts", edit_below)
    act("gate's band edited", edit_band)
    act("let go", win.let_go)
    return out


def slope(xs, ys):
    """The least-squares slope of log y on log x; a size of 0 is taken as 1 and every size one more, so 0, 2, 6 is 1, 3, 7."""
    shift = 1 if 0 in xs else 0
    lx, ly = [math.log(x + shift) for x in xs], [math.log(max(y, 1)) for y in ys]
    mx, my = sum(lx) / len(lx), sum(ly) / len(ly)
    return sum((a - mx) * (b - my) for a, b in zip(lx, ly)) / sum((a - mx) ** 2 for a in lx)


findings = []
print(f"cut by {G['CUTTER']}; base {BASE}\n")
print("| act | size | at once: steps smallest to largest | exponent | to be | until settled: steps | exponent | to be |")
print("|---|---|---|---|---|---|---|---|")
for dim in (ASKED or SIZES):
    runs = [(v, measured(f"{dim.replace(' ', '-')}-{v}", {**BASE, dim: v})) for v in SIZES[dim]]
    xs = [v for v, _ in runs]
    for name, expected in EXPECTED.items():
        cells = []
        for part, to_be in zip((0, 1), expected):
            ys = [sum(got[name][part].values()) for _, got in runs]
            k, want = slope(xs, ys), to_be.get(dim, 0)
            over = k > want + OVER and ys[-1] > NOISE
            cells += [f"{ys[0]} to {ys[-1]}", f"{'**' if over else ''}{k:.2f}{'**' if over else ''}", str(want)]
            if over:
                first, last = runs[0][1][name][part], runs[-1][1][name][part]
                grew = sorted(((n - first.get(f, 0), f) for f, n in last.items()), reverse=True)[:5]
                findings.append((k - want, f"{name}, {'at once' if part == 0 else 'until settled'}, by {dim}: {k:.2f} where {want} is expected, "
                                           f"{ys[0]} to {ys[-1]} steps; " + ", ".join(f"{f} +{more}" for more, f in grew)))
        print(f"| {name} | {dim} | " + " | ".join(cells) + " |")
    sys.stdout.flush()
print(f"\n{len(findings)} cells over what is expected by more than {OVER}, the furthest first:")
for _, said in sorted(findings, reverse=True):
    print(" -", said)
sys.stdout.flush()
import os  # noqa: E402

os._exit(0)
