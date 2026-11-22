"""The player in miniature, held to the oracles of docs/playground/JOURNAL.md that take the whole
player to ask: O7, what one more cut in time costs does not grow with how many there are; O8, a
bare walk and a clip walk hold the same; O9, nothing walked for the window is held, and a clip
walk holds the same whatever the window walked first; O10, the window shows a line of every
series node the document has, a clip walk made or not; O11, a document and its checkpoint taken to
another folder and a results folder of nothing open where they were left.

The player's own window, worker, plan, held runs and tools, offscreen, over a clip of tiny frames
made here whose gray cycles so that a banded `reduce` gates a `period` into one cut every PERIOD
rows, with `reduce` and `smooth` below it. The worker's thread is never started: its turns are
taken here, one at a time, and its signals land in the window's slots inside the turn, so a run
is one thread and the calls it makes are the same every time. A clip walk is asked and turned to
its end at two counts of cuts with every line run and every jump back counted to its function,
so a loop that calls nothing is counted as one that does; a function is said to grow where its
steps a cut at the larger count pass GROWS times those at the smaller. The monitor's modules are
left out: the clock turns them, and what they cost a cut is not seen here. O8 to O11 are asked of
clips of CHECKED cuts; the bare walk is bare.main's, in this process. No checkpoint is written but
O11's, whose document is its own: detect below threshold, whose tables the keeper keeps, and size.

Run: .venv/Scripts/python.exe -X utf8 docs/playground/sim/miniature.py [tree] [small large]
`tree` is a checkout of the repository to drive, this one with none; `0 0` leaves O7 out. Exit 1
where an oracle fails.
With MINIATURE_WHY set to a function's name, the larger count is walked under cProfile as well and
who called it is printed.
"""
import contextlib
import cProfile
import io
import json
import os
import pickle
import pstats
import sys
import tempfile
from pathlib import Path

args = sys.argv[1:]
TREE = Path(args.pop(0)).resolve() if args and not args[0].isdigit() else Path(__file__).resolve().parents[3]
SMALL, LARGE = (int(a) for a in args) if args else (200, 800)     # the smaller clip is several windows long, so neither count is mostly the window's own rows
PERIOD, KEPT = 8, 4     # rows from one cut's first row to the next's, and the rows of a cut
GROWS = 1.5
CHECKED = 40
SHOWN = 12

SCRATCH = tempfile.mkdtemp(prefix="sieve-miniature-")
os.environ.update(QT_QPA_PLATFORM="offscreen", SIEVE_STORE=os.path.join(SCRATCH, "store"), SIEVE_RESULTS=os.path.join(SCRATCH, "results"))
sys.path.insert(0, str(TREE))
os.chdir(TREE)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import bare, decoder, held, result_keeper, store, window  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.stream import HAND  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

store.CHOICE = os.path.join(SCRATCH, "store.txt")
decoder.read_frame_times_ahead = lambda path, then=None: None
decoder.STORE = None
decoder.QUIET = True
WRITE, held.File.write = held.File.write, lambda self, *a: []
window.TELL = 0.0                   # every row told: no telling waits on a clock
Worker.start = lambda self, *a: None
window.PlayerWindow.ask_unsaved = lambda self: "discard"
app = QApplication([])
TOOLS = [e for e in discover("tools") if e.ok]


def clip(path, cuts):
    """A clip of `cuts` * PERIOD rows whose first KEPT rows of each PERIOD are bright."""
    wr = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 30, (64, 48))
    for r in range(cuts * PERIOD):
        wr.write(np.full((48, 64, 3), 200 if r % PERIOD < KEPT else 20, np.uint8))
    wr.release()
    return str(path)


def document(path, video):
    doc = D.Document(video=video)
    doc.add_node(D.VIDEO_TOOL)
    for nid, tool, src, into in (("gray", "gray", D.VIDEO_TOOL, None), ("gate", "reduce", "gray", None), ("period", "period", "gray", None),
                                 ("below", "reduce", "period", None), ("smooth", "smooth", "below", None), (None, None, "gate", "gate")):
        if tool is not None:
            doc.add_node(tool, (0.0, 100.0 * len(doc.nodes)), None, nid)
        doc.connect(src, nid or "period", *([into] if into else []))
    doc.node("gate").band = (100.0, 255.0)
    D.save(doc, path)
    return str(path)


def turned(win):
    """Takes the worker's turns until none is due."""
    w, g = win.worker, win.graph
    while True:
        with w._cv:
            turn = w._turn()
        if turn is None:
            return
        for job, act in turn[1]:
            g.serving(turn[0], job.name)
            act()


def opened(name, cuts=CHECKED):
    """A player on a clip of `cuts` cuts made under `name`, its first window walked."""
    folder = Path(SCRATCH) / name
    folder.mkdir()
    win = window.PlayerWindow(document(folder / "doc.json", clip(folder / "v.avi", cuts)), "t", TOOLS)
    if win.playing:
        win.toggle_play()
    turned(win)
    return win


def settled(win):
    for _ in range(4):          # a held run makes cuts, whose runs held may make more: turned until nothing is due
        turned(win)
        app.processEvents()


def holds(win):
    """(node, its cut's rows or None, first row) -> the signal held of it under the key the node now has."""
    return {(nid, run.cut, run.start): r["signal"] for run in win.runs for nid, r in run.results.items() if held.good(r, win._key(nid))}


def apart(a, b):
    """What `a` and `b`, each as `holds` answers, do not hold alike."""
    return sorted(map(str, a.keys() ^ b.keys())) + sorted(str(k) for k in a.keys() & b.keys()
                                                         if not np.array_equal(a[k], b[k], equal_nan=a[k].dtype.kind == "f"))


def bare_and_clip():
    """O8: what a bare walk's file leaves held, before the worker has a turn, against a clip walk's."""
    by_clip = opened("clip")
    by_clip._toggle_clip()
    settled(by_clip)
    by_bare = opened("bare")
    job, out = Path(SCRATCH) / "bare" / "job.json", Path(SCRATCH) / "bare" / "results.pkl"
    job.write_text(json.dumps(bare.job(by_bare.doc, by_bare.decoder.path, by_bare.tools, str(out))), encoding="utf-8")
    with contextlib.redirect_stdout(io.StringIO()) as said:
        code = bare.main(str(job))
    if code:
        return [f"the bare walk ended with {code}: {said.getvalue().splitlines()[-1]}"]
    with open(out, "rb") as f:
        left = pickle.load(f)
    by_bare._take_bare(*left) if hasattr(by_bare, "_take_bare") else by_bare._clip_ready(*left)
    want = holds(by_clip)
    return [f"a clip walk holds {len(want)} results and none"] * (not want) + apart(want, holds(by_bare))


def window_first():
    """O9: a window walked at three places holds nothing, and with it walked there and an edit below
    the period made after a clip walk, what is held is what a clip walk of the edited document holds."""
    win = opened("first")
    for at in (0, 2 * PERIOD + 1, CHECKED * PERIOD // 2):
        win.set_window(at, win.window_[1], by=HAND)
        settled(win)
    said = [f"{len(list(win.runs))} runs held of a window's walks alone"] * bool(list(win.runs))
    win._toggle_clip()
    settled(win)
    win.doc.node("smooth").params["reach"] += 2
    win._params_changed("smooth")
    for at in (3 * PERIOD, 0):
        win.set_window(at, win.window_[1], by=HAND)
        settled(win)
    alone = opened("alone")
    alone.doc.node("smooth").params["reach"] += 2
    alone._params_changed("smooth")
    alone._toggle_clip()
    settled(alone)
    want = holds(alone)
    return said + [f"a clip walk holds {len(want)} results and none"] * (not want) + apart(want, holds(win))


def window_shows():
    """O10: the series nodes the plot has no line of, in a player opened and no clip walk asked, and after one."""
    win = opened("shows")
    nodes = {"gate", "below", "smooth"}
    said = [f"no line of {nid} before a clip walk" for nid in sorted(nodes - set(win.plot.lines))]
    win._toggle_clip()
    settled(win)
    return said + [f"no line of {nid} after a clip walk" for nid in sorted(nodes - set(win.plot.lines))]


def checkpoint_travels():
    """O11: a document saved with its checkpoint, copied to another folder and opened with an empty
    results folder, serves every run the first player held without walking, and after an edit below
    a frame node that makes small rows, a clip walk runs that frame node zero times; opened with the
    checkpoint's kept rows withheld, it runs it again, or the check would show nothing."""
    by_name = {e.name: e.module for e in TOOLS}
    detect, ran, said = by_name["detect"], [0], []
    run = detect.run

    def counted(frames, row, params):
        ran[0] += 1
        return run(frames, row, params)

    def player(folder):
        os.environ["SIEVE_RESULTS"] = str(folder / "results")       # a Keeper over a root of nothing
        win = window.PlayerWindow(str(folder / "doc.json"), "t", TOOLS)
        if win.playing:
            win.toggle_play()
        return win

    def edited_and_walked(win):
        size = next(n.id for n in win.doc.nodes if n.tool == "size")
        win.doc.node(size).params["method"] = "max"
        win._params_changed(size)
        ran[0] = 0
        win._toggle_clip()
        settled(win)
        return ran[0], size

    home, results = Path(SCRATCH) / "travels", os.environ["SIEVE_RESULTS"]
    home.mkdir()
    doc = D.from_tools([by_name[n] for n in ("gray", "threshold", "detect", "size")], "v.avi")
    clip(home / "v.avi", CHECKED)
    D.save(doc, home / "doc.json")
    held.File.write = WRITE
    detect.run = counted
    try:
        first = player(home)
        turned(first)
        first._toggle_clip()
        settled(first)
        first.save_document()
        want = holds(first)
        said += [f"the first player holds {len(want)} results and none"] * (not want)
        for name, withheld in (("colleague", False), ("withheld", True)):
            away = Path(SCRATCH) / name
            away.mkdir()
            for f in ("doc.json", "v.avi", Path(held.path_for("doc.json")).name):
                (away / f).write_bytes((home / f).read_bytes())
            lend = result_keeper.Keeper.lend
            if withheld:
                result_keeper.Keeper.lend = lambda self, chunks: None
            try:
                ran[0] = 0
                win = player(away)
                got = holds(win)
                turned(win)
                opened_ran = ran[0]
                walked_ran, size = edited_and_walked(win)
            finally:
                result_keeper.Keeper.lend = lend
            if withheld:
                said += [f"with the kept rows withheld the clip walk ran detect {walked_ran} times"] * (not walked_ran)
                continue
            said += apart(want, got) + [f"detect ran {opened_ran} times as it opened"] * bool(opened_ran)
            said += [f"detect ran {walked_ran} times in the clip walk after the edit"] * bool(walked_ran)
            said += [f"the clip walk after the edit held no size of {win.count} rows"] * (
                not any(nid == size and len(v) == win.count for (nid, _, _), v in holds(win).items()))
    finally:
        held.File.write, detect.run = (lambda self, *a: []), run
        os.environ["SIEVE_RESULTS"] = results
    return said


TOOL = sys.monitoring.COVERAGE_ID
EVENTS = sys.monitoring.events.LINE | sys.monitoring.events.JUMP


CLOCKED = ("machine.py", "ledger.py", "catalogue.py")      # the monitor's: turned by the clock, so their steps follow how long a run took


def named(code):
    fn = code.co_filename
    if fn == "<string>":
        return f"generated:{code.co_name}"      # a dataclass's __eq__, which a search by equality runs once a candidate
    own = "sieve_player" in fn or os.sep + "tools" + os.sep in fn
    return f"{Path(fn).name}:{code.co_name}" if own and Path(fn).name not in CLOCKED else None


def walked(cuts, callers=False):
    """function of the player or a tool -> its lines run and jumps back, over a clip walk of `cuts`
    cuts turned to its end; the cuts held; and with `callers` a cProfile of the same."""
    win = opened(str(cuts), cuts)
    steps, names = {}, {}

    def step(code, *_):
        name = names.get(code)
        if name is None:
            name = names[code] = named(code) or False
        if name is False:
            return sys.monitoring.DISABLE
        steps[name] = steps.get(name, 0) + 1

    prof = cProfile.Profile() if callers else None
    sys.monitoring.use_tool_id(TOOL, "miniature")
    sys.monitoring.register_callback(TOOL, sys.monitoring.events.LINE, step)
    sys.monitoring.register_callback(TOOL, sys.monitoring.events.JUMP, step)
    sys.monitoring.set_events(TOOL, EVENTS)
    if prof:
        prof.enable()
    win._toggle_clip()
    settled(win)
    if prof:
        prof.disable()
    sys.monitoring.set_events(TOOL, 0)
    sys.monitoring.free_tool_id(TOOL)
    return steps, sum(run.cut is not None for run in win.runs), prof


failed = False
if LARGE:
    small, held_small, _ = walked(SMALL)
    large, held_large, prof = walked(LARGE, bool(os.environ.get("MINIATURE_WHY")))
    print(f"{TREE.name}: {held_small} of {SMALL} cuts held, {held_large} of {LARGE}; steps a cut {sum(small.values()) / SMALL:.0f} and {sum(large.values()) / LARGE:.0f}")
    grew = sorted(((large[f] / LARGE) / (n / SMALL), large[f] / LARGE, n / SMALL, f) for f, n in small.items()
                  if n >= SMALL and f in large and large[f] / LARGE > GROWS * n / SMALL)
    for ratio, at_large, at_small, f in grew[::-1][:SHOWN]:
        print(f"  grows {ratio:5.1f}x  {at_small:9.1f} -> {at_large:9.1f} steps a cut  {f}")
    failed = bool(grew) or (held_small, held_large) != (SMALL, LARGE)
    if (held_small, held_large) != (SMALL, LARGE):
        print("O7 is not shown: the cuts were not all walked and held")
    else:
        print(f"O7 {'fails' if grew else 'holds'}: {len(grew)} functions' steps a cut grew past {GROWS}x from {SMALL} cuts to {LARGE}")
    if prof:
        pstats.Stats(prof, stream=sys.stdout).strip_dirs().print_callers(os.environ["MINIATURE_WHY"])
for oracle, check in (("O8", bare_and_clip), ("O9", window_first), ("O10", window_shows), ("O11", checkpoint_travels)):
    try:
        said = check()
    except Exception as e:
        said = [f"{type(e).__name__}: {e}"]
    print(f"{oracle} {'fails' if said else 'holds'}: {check.__doc__.split(':', 1)[1].strip().split(chr(10))[0] if not said else ''}"
          + "".join(f"\n  {line}" for line in said[:SHOWN]) + (f"\n  and {len(said) - SHOWN} more" if len(said) > SHOWN else ""))
    failed = failed or bool(said)
sys.stdout.flush()
os._exit(1 if failed else 0)
