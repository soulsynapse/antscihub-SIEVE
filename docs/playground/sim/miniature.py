"""The player in miniature, held to the oracles of docs/playground/JOURNAL.md that take the whole
player to ask: O7, what one more cut in time costs does not grow with how many there are; O8, a
bare walk and a clip walk hold the same; O9, nothing walked for the window is held, written to
the checkpoint or to the store, and a clip walk holds the same whatever the window walked first;
O10, the window shows a line of every series node the document has over its rows, a clip walk
made or not, best effort where a period runs on past the window and no clip walk was made; O11, a full run made and the document
saved, the two copied elsewhere and opened serve every run held without walking; O14, a held run
made under a tool's older code is served after the code changes, its node marked as of other code.

The player's own window, worker, plan, held runs and tools, offscreen, over a clip of tiny frames
made here whose gray cycles so that a banded `reduce` gates a `period` into one cut every PERIOD
rows, with `reduce` and `smooth` below it. The worker's thread is never started: its turns are
taken here, one at a time, and its signals land in the window's slots inside the turn, so a run
is one thread and the calls it makes are the same every time. A clip walk is asked and turned to
its end at two counts of cuts with every line run and every jump back counted to its function,
so a loop that calls nothing is counted as one that does; a function is said to grow where its
steps a cut at the larger count pass GROWS times those at the smaller; and a window moved with the
larger count held is not to take GROWS times the steps of one with the smaller, the steps of one
with none held printed beside them. The monitor's modules are
left out: the clock turns them, and what they cost a cut is not seen here. O8 to O11 are asked of
clips of CHECKED cuts; the bare walk is bare.main's, in this process. No checkpoint is written but
O11's and O14's, which have a document of their own: gray, threshold, detect and size, detect's
runs counted. O14 changes what the registry says of detect's code, as imported and as on disk,
and edits no file.

Run: .venv/Scripts/python.exe -X utf8 docs/playground/sim/miniature.py [tree] [small large]
`tree` is a checkout of the repository to drive, this one with none; `0 0` leaves O7 out. Exit 1
where an oracle fails.
With MINIATURE_CUTTER set, the cutting node is not a `period` cut by its gate's runs: `pad1` and
`pad3` make it a `pad` of sim/cutters/ widening each run by that many rows, the second overlapping
its neighbours; `nested` puts a second gate and `period` below the first, cutting the same rows.
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
os.environ.update(QT_QPA_PLATFORM="offscreen", SIEVE_STORE=os.path.join(SCRATCH, "store"))
sys.path.insert(0, str(TREE))
os.chdir(TREE)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import bare, decoder, held, registry, store, window  # noqa: E402
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
TOOLS = [e for e in discover("tools", str(Path(__file__).resolve().parent / "cutters")) if e.ok]
CUTTER = os.environ.get("MINIATURE_CUTTER", "period")
PAD = {"pad1": 1, "pad3": 3}.get(CUTTER, 0)
NESTED = CUTTER == "nested"


def cuts_of(count):
    """[first, end) of every cut the document's cutting node makes of a clip `count` rows long."""
    return [(max(0, a - PAD), min(count, a + KEPT + PAD)) for a in range(0, count, PERIOD)]


def clip(path, cuts):
    """A clip of `cuts` * PERIOD rows whose first KEPT rows of each PERIOD are bright."""
    wr = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 30, (64, 48))
    for r in range(cuts * PERIOD):
        wr.write(np.full((48, 64, 3), 200 if r % PERIOD < KEPT else 20, np.uint8))
    wr.release()
    return str(path)


LOWEST = "inner" if NESTED else "period"     # the cutting node the series nodes read
BELOW = (("below", "reduce", LOWEST), ("smooth", "smooth", "below"))
INNER = (("gate2", "reduce", "period", None), ("inner", "period", "period", None), ("inner", None, "gate2", "gate")) if NESTED else ()


def document(path, video):
    """gray, a gate and the cutting node it cuts, `period` or with MINIATURE_CUTTER pad1 or pad3 a
    `pad` of that many rows, and BELOW; with nested, a second gate below the period cutting a
    second period by the same band, whose cuts are the first's."""
    doc = D.Document(video=video)
    doc.add_node(D.VIDEO_TOOL)
    for nid, tool, src, into in (("gray", "gray", D.VIDEO_TOOL, None), ("gate", "reduce", "gray", None),
                                 ("period", "pad" if PAD else "period", "gray", None), ("period", None, "gate", "gate"),
                                 *INNER, *((n, t, s, None) for n, t, s in BELOW)):
        if tool is not None:
            doc.add_node(tool, (0.0, 100.0 * len(doc.nodes)), None, nid)
        doc.connect(src, nid, *([into] if into else []))
    for gate in ("gate", "gate2")[:1 + NESTED]:
        doc.node(gate).band = (100.0, 255.0)
    if PAD:
        doc.node("period").params["pad"] = PAD
    D.save(doc, path)
    return str(path)


def turned(win):
    """Takes the worker's turns until none is due, the window's wait to answer of every cut over at once."""
    w, g = win.worker, win.graph
    while True:
        with w._cv:
            turn = w._turn()
        if turn is None and win._whole_due.isActive():
            win._show_held_whole()
            continue
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


def stored():
    """Every file under the store's folder."""
    return {str(Path(d) / f) for d, _, fs in os.walk(store.folder()) for f in fs}


def window_first():
    """O9: a window walked at three places and the document saved holds nothing, writes no run to
    the checkpoint and no file to the store, a clip walk then holds what a clip walk alone holds,
    and with it walked there and an edit below the period, what a clip walk of the edited document holds."""
    had = stored()
    held.File.write = WRITE
    try:
        win = opened("first")
        for at in (0, 2 * PERIOD + 1, CHECKED * PERIOD // 2):
            win.set_window(at, win.window_[1], by=HAND)
            settled(win)
        win.save_document()
        win._write_held(wait=True)
    finally:
        held.File.write = lambda self, *a: []
    said = [f"{len(list(win.runs))} runs held of a window's walks alone"] * bool(list(win.runs))
    written = held.File(held.path_for(win.doc.path)).load()
    said += [f"the checkpoint holds {len(written)} runs of a window's walks alone"] * bool(written)
    said += [f"the store holds {f} of a window's walks alone" for f in sorted(stored() - had)]
    win._toggle_clip()
    settled(win)
    by_clip = opened("first-alone")
    by_clip._toggle_clip()
    settled(by_clip)
    want = holds(by_clip)
    said += [f"after the windows: {d}" for d in apart(want, holds(win))]
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


WINDOWS = (("inside a period", 5 * PERIOD + 1, 2), ("over two whole periods", 3 * PERIOD - 2, 2 * PERIOD),
           ("cutting periods at both edges", 2 * PERIOD + 2, 2 * PERIOD),
           ("between two of the gate's runs", 3 * PERIOD + KEPT, PERIOD - KEPT - 1))    # rows of a cut only where a cut reads past its gate's run


def drawn(win, nid, s, n):
    """(the rows of the window `nid`'s line covers, those of them said best effort)."""
    rows, best = set(), set()
    for line in win.plot.lines[nid].pieces if nid in win.plot.lines else []:
        got = set(range(line.start, line.start + len(line.values))) & set(range(s, s + n))
        rows |= got
        best |= got if line.best else set()
    return rows, best


def lines_over(win, when, cut_off):
    """What of the period's rows in each of WINDOWS the lines below it miss, and where they are said
    best effort other than at a period cut off at the window's edge, where `cut_off` says they are."""
    said = []
    for name, s, n in WINDOWS:
        win.set_window(s, n, by=HAND)
        settled(win)
        window, cuts = set(range(s, s + n)), cuts_of(win.count)
        want = {r for a, b in cuts for r in range(a, b)} & window
        edges = {r for a, b in cuts if a < s or b > s + n for r in range(a, b)} & window if cut_off else set()
        for nid in (nid for nid, *_ in BELOW):
            rows, best = drawn(win, nid, s, n)
            said += [f"{when}, a window {name}: {nid} draws {len(rows & want)} of its {len(want)} rows of periods"] * (rows != want)
            said += [f"{when}, a window {name}: {nid} is best effort at {len(best)} rows and is to be at {len(edges)}"] * (best != edges)
    return said


def window_shows():
    """O10: the series nodes the plot has no line of, in a player opened and no clip walk asked, and
    after one; and over windows inside a period, over whole ones and cutting them, the period's rows
    the lines below it miss, best effort at a period cut off at the window's edge before a clip walk alone."""
    win = opened("shows")
    nodes = {"gate", *(nid for nid, *_ in BELOW), *(["gate2"] if NESTED else [])}
    said = [f"no line of {nid} before a clip walk" for nid in sorted(nodes - set(win.plot.lines))]
    said += lines_over(win, "before a clip walk", True)
    win._toggle_clip()
    settled(win)
    win.set_window(0, round(10 * win.fps), by=HAND)
    settled(win)
    said += [f"no line of {nid} after a clip walk" for nid in sorted(nodes - set(win.plot.lines))]
    return said + lines_over(win, "after a clip walk", False)


BY_NAME = {e.name: e.module for e in TOOLS}
DETECT, RAN = BY_NAME["detect"], []     # O11's and O14's frame node, and the rows it ran at
RUN = DETECT.run


def counted_run(frames, row, params):
    RAN.append(row)
    return RUN(frames, row, params)


def tables_home(name):
    """A folder of a clip of CHECKED cuts and a document of gray, threshold, detect and size over it."""
    home = Path(SCRATCH) / name
    home.mkdir()
    doc = D.from_tools([BY_NAME[n] for n in ("gray", "threshold", "detect", "size")], "v.avi")
    clip(home / "v.avi", CHECKED)
    D.save(doc, home / "doc.json")
    return home


def copied(home, name):
    """The document, clip and checkpoint of `home` copied to a folder `name` of nothing else."""
    away = Path(SCRATCH) / name
    away.mkdir()
    for f in ("doc.json", "v.avi", Path(held.path_for("doc.json")).name):
        (away / f).write_bytes((home / f).read_bytes())
    return away


def player(folder):
    """A player on the document saved in `folder`, not playing, its worker not turned."""
    win = window.PlayerWindow(str(folder / "doc.json"), "t", TOOLS)
    if win.playing:
        win.toggle_play()
    return win


def saved_full_run(name):
    """A folder `name` whose document had a clip walk and was saved, its checkpoint written, and
    what its player held; the caller sets held.File.write to WRITE first."""
    home = tables_home(name)
    first = player(home)
    turned(first)
    first._toggle_clip()
    settled(first)
    first.save_document()
    return home, holds(first)


def served_unwalked(want, folder):
    """A player of the document in `folder`, opened and turned with detect counted, and what of
    `want` it does not serve, or the rows detect ran at for a walk: at any but the playhead's,
    which the display draws and no checkpoint holds."""
    DETECT.run = counted_run
    RAN.clear()
    try:
        win = player(folder)
        got = holds(win)
        turned(win)
    finally:
        DETECT.run = RUN
    walked = [r for r in RAN if r != win.row]
    return win, [f"the first player holds {len(want)} results and none"] * (not want) + apart(want, got) + (
        [f"detect ran at {len(walked)} rows besides the playhead's as it opened"] * bool(walked))


def checkpoint_travels():
    """O11: a full run made and the document saved, the document and its checkpoint copied
    elsewhere and opened: every run the first player held is served without walking."""
    held.File.write = WRITE
    try:
        home, want = saved_full_run("travels")
        return served_unwalked(want, copied(home, "colleague"))[1]
    finally:
        held.File.write = lambda self, *a: []


def other_code():
    """O14: a held run made under a tool's older code is served after the tool's code changes, and
    its node is marked as of other code, a node below a cut in time as one above: a full run saved, then detect's code said changed, as the
    process imported it and as its file lies, and a player of a copy opened."""
    held.File.write = WRITE
    imported, on_disk = registry._IMPORTED[id(DETECT)], registry.code_print
    try:
        home, want = saved_full_run("other-code")
        registry._IMPORTED[id(DETECT)] = (DETECT, "other code")
        registry.code_print = lambda tool, seen=None: "other code" if tool is DETECT else on_disk(tool, seen)
        win, said = served_unwalked(want, copied(home, "other-code-away"))
        marks = {}
        win.pane.set_stale = lambda nid, tip: marks.__setitem__(nid, bool(tip))
        win._show_stale()
        detect = next(n.id for n in win.doc.nodes if n.tool == "detect")
        said += [f"{detect} is not marked as of other code"] * (not marks.get(detect))
        cut, reduce_ = opened("other-code-cut"), BY_NAME["reduce"]
        cut._toggle_clip()
        settled(cut)
        registry.code_print = lambda tool, seen=None: "other code" if tool is reduce_ else on_disk(tool, seen)
        marks = {}
        cut.pane.set_stale = lambda nid, tip: marks.__setitem__(nid, bool(tip))
        cut._show_stale()
        return said + [f"{nid}, of a tool of other code and below a cut in time, is not marked" for nid, tool, _ in BELOW if tool == "reduce" and not marks.get(nid)]
    finally:
        held.File.write, registry.code_print = (lambda self, *a: []), on_disk
        registry._IMPORTED[id(DETECT)] = imported


TOOL = sys.monitoring.COVERAGE_ID
EVENTS = sys.monitoring.events.LINE | sys.monitoring.events.JUMP


CLOCKED = ("machine.py", "ledger.py", "catalogue.py")      # the monitor's: turned by the clock, so their steps follow how long a run took


def named(code):
    fn = code.co_filename
    if fn == "<string>":
        return f"generated:{code.co_name}"      # a dataclass's __eq__, which a search by equality runs once a candidate
    own = "sieve_player" in fn or os.sep + "tools" + os.sep in fn
    return f"{Path(fn).name}:{code.co_name}" if own and Path(fn).name not in CLOCKED else None


def stepped(act, prof=None):
    """function of the player or a tool -> its lines run and jumps back over `act()`, `prof` a
    cProfile enabled over the same where one is handed."""
    steps, names = {}, {}

    def step(code, *_):
        name = names.get(code)
        if name is None:
            name = names[code] = named(code) or False
        if name is False:
            return sys.monitoring.DISABLE
        steps[name] = steps.get(name, 0) + 1

    sys.monitoring.use_tool_id(TOOL, "miniature")
    sys.monitoring.register_callback(TOOL, sys.monitoring.events.LINE, step)
    sys.monitoring.register_callback(TOOL, sys.monitoring.events.JUMP, step)
    sys.monitoring.set_events(TOOL, EVENTS)
    if prof:
        prof.enable()
    act()
    if prof:
        prof.disable()
    sys.monitoring.set_events(TOOL, 0)
    sys.monitoring.free_tool_id(TOOL)
    return steps


def walked(cuts, callers=False):
    """Over a clip walk of `cuts` cuts turned to its end: function of the player or a tool -> its
    lines run and jumps back; the cuts held; with `callers` a cProfile of the same; and the player."""
    win = opened(str(cuts), cuts)
    prof = cProfile.Profile() if callers else None
    steps = stepped(lambda: (win._toggle_clip(), settled(win)), prof)
    return steps, sum(run.cut is not None for run in win.runs), prof, win


def window_moved(win):
    """The steps of the player and the tools over the window moved to the middle of the clip and turned to its end."""
    return sum(stepped(lambda: (win.set_window(win.count // 2, win.window_[1], by=HAND), settled(win))).values())


failed = False
if LARGE:
    small, held_small, _, win_small = walked(SMALL)
    large, held_large, prof, win_large = walked(LARGE, bool(os.environ.get("MINIATURE_WHY")))
    moved_small, moved_large = window_moved(win_small), window_moved(win_large)
    moved_grew = moved_large > GROWS * moved_small
    print(f"a window moved: {moved_small} steps with {SMALL} cuts held, {moved_large} with {LARGE}, "
          f"{window_moved(opened(f'{SMALL}-unheld', SMALL))} with none held of {SMALL}")
    print(f"{TREE.name}, cut by {CUTTER}: {held_small} of {SMALL} cuts held, {held_large} of {LARGE}; steps a cut {sum(small.values()) / SMALL:.0f} and {sum(large.values()) / LARGE:.0f}")
    grew = sorted(((large[f] / LARGE) / (n / SMALL), large[f] / LARGE, n / SMALL, f) for f, n in small.items()
                  if n >= SMALL and f in large and large[f] / LARGE > GROWS * n / SMALL)
    for ratio, at_large, at_small, f in grew[::-1][:SHOWN]:
        print(f"  grows {ratio:5.1f}x  {at_small:9.1f} -> {at_large:9.1f} steps a cut  {f}")
    failed = bool(grew) or moved_grew or (held_small, held_large) != (SMALL * (1 + NESTED), LARGE * (1 + NESTED))
    if (held_small, held_large) != (SMALL * (1 + NESTED), LARGE * (1 + NESTED)):
        print("O7 is not shown: the cuts were not all walked and held")
    else:
        print(f"O7 {'fails' if grew or moved_grew else 'holds'}: {len(grew)} functions' steps a cut grew past {GROWS}x from {SMALL} cuts to {LARGE}, "
              f"and a window moved {'grew' if moved_grew else 'did not grow'} past {GROWS}x ({moved_large / moved_small:.2f}x)")
    if prof:
        pstats.Stats(prof, stream=sys.stdout).strip_dirs().print_callers(os.environ["MINIATURE_WHY"])
for oracle, check in (("O8", bare_and_clip), ("O9", window_first), ("O10", window_shows), ("O11", checkpoint_travels), ("O14", other_code)):
    try:
        said = check()
    except Exception as e:
        said = [f"{type(e).__name__}: {e}"]
    print(f"{oracle} {'fails' if said else 'holds'}: {check.__doc__.split(':', 1)[1].strip().split(chr(10))[0] if not said else ''}"
          + "".join(f"\n  {line}" for line in said[:SHOWN]) + (f"\n  and {len(said) - SHOWN} more" if len(said) > SHOWN else ""))
    failed = failed or bool(said)
sys.stdout.flush()
os._exit(1 if failed else 0)
