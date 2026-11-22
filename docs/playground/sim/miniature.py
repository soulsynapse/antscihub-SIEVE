"""The player in miniature, held to O7 of docs/playground/JOURNAL.md: what one more cut in time
costs does not grow with how many there are.

The player's own window, worker, plan, held runs and tools, offscreen, over a clip of tiny frames
made here whose gray cycles so that a banded `reduce` gates a `period` into one cut every PERIOD
rows, with `reduce` and `smooth` below it. The worker's thread is never started: its turns are
taken here, one at a time, and its signals land in the window's slots inside the turn, so a run
is one thread and the calls it makes are the same every time. A clip walk is asked and turned to
its end at two counts of cuts with every line run and every jump back counted to its function,
so a loop that calls nothing is counted as one that does; a function is said to grow where its
steps a cut at the larger count pass GROWS times those at the smaller. The monitor's modules are
left out: the clock turns them, and what they cost a cut is not seen here.

Run: .venv/Scripts/python.exe -X utf8 docs/playground/sim/miniature.py [tree] [small large]
`tree` is a checkout of the repository to drive, this one with none. Exit 1 where a function grows.
With MINIATURE_WHY set to a function's name, the larger count is walked under cProfile as well and
who called it is printed.
"""
import cProfile
import os
import pstats
import sys
import tempfile
from pathlib import Path

args = sys.argv[1:]
TREE = Path(args.pop(0)).resolve() if args and not args[0].isdigit() else Path(__file__).resolve().parents[3]
SMALL, LARGE = (int(a) for a in args) if args else (200, 800)     # the smaller clip is several windows long, so neither count is mostly the window's own rows
PERIOD, KEPT = 8, 4     # rows from one cut's first row to the next's, and the rows of a cut
GROWS = 1.5
SHOWN = 12

SCRATCH = tempfile.mkdtemp(prefix="sieve-miniature-")
os.environ.update(QT_QPA_PLATFORM="offscreen", SIEVE_STORE=os.path.join(SCRATCH, "store"), SIEVE_RESULTS=os.path.join(SCRATCH, "results"))
sys.path.insert(0, str(TREE))
os.chdir(TREE)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder, held, store, window  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

store.CHOICE = os.path.join(SCRATCH, "store.txt")
decoder.read_frame_times_ahead = lambda path, then=None: None
decoder.STORE = None
decoder.QUIET = True
held.File.write = lambda self, runs: []
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
    folder = Path(SCRATCH) / str(cuts)
    folder.mkdir()
    win = window.PlayerWindow(document(folder / "doc.json", clip(folder / "v.avi", cuts)), "t", TOOLS)
    if win.playing:
        win.toggle_play()
    turned(win)
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
    for _ in range(4):          # a held run makes cuts, whose runs held may make more: turned until nothing is due
        turned(win)
        app.processEvents()
    if prof:
        prof.disable()
    sys.monitoring.set_events(TOOL, 0)
    sys.monitoring.free_tool_id(TOOL)
    return steps, sum(run.cut is not None for run in win.runs), prof


small, held_small, _ = walked(SMALL)
large, held_large, prof = walked(LARGE, bool(os.environ.get("MINIATURE_WHY")))
print(f"{TREE.name}: {held_small} of {SMALL} cuts held, {held_large} of {LARGE}; steps a cut {sum(small.values()) / SMALL:.0f} and {sum(large.values()) / LARGE:.0f}")
if (held_small, held_large) != (SMALL, LARGE):
    print("the cuts were not all walked and held: nothing is shown of O7")
    sys.stdout.flush()
    os._exit(2)
grew = sorted(((large[f] / LARGE) / (n / SMALL), large[f] / LARGE, n / SMALL, f) for f, n in small.items()
              if n >= SMALL and f in large and large[f] / LARGE > GROWS * n / SMALL)
for ratio, at_large, at_small, f in grew[::-1][:SHOWN]:
    print(f"  grows {ratio:5.1f}x  {at_small:9.1f} -> {at_large:9.1f} steps a cut  {f}")
print(f"O7 {'fails' if grew else 'holds'}: {len(grew)} functions' steps a cut grew past {GROWS}x from {SMALL} cuts to {LARGE}")
if prof:
    pstats.Stats(prof, stream=sys.stdout).strip_dirs().print_callers(os.environ["MINIATURE_WHY"])
sys.stdout.flush()
os._exit(1 if grew else 0)
