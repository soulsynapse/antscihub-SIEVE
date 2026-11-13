"""The monitor leading with what is wrong, offscreen, on the simulations' graph: faults built at once,
a memo under half the window, a plate cache of eight rows, a tool reading half a clip away and a chain node run whole, their
lines read in order of cost; each picked in turn and the marks read, in the table, the stacks, the
panels and on the axis; the copy of one and of all; the window paused over a walk and resumed; and
sized to its smallest. Then a ledger fed runs of two known costs and a machine sample, the quantiles
and the bucket read; the healthy graph with the machine sampled every tenth of a second: the shapes on
the events, the table's columns against the walk's record, the time view's default and a track added,
the machine's panel against the OS's own, with memory's limit as it is and set low, and the copy of
two problems. Then a window that does not fit its memo, the need read at each row before the first
discard and beside what an unbounded memo then held. Prints each and exits 1 where one is not so; with
a folder as the argument the monitor is grabbed there.

    .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-12-the-window-says-what-is-wrong.py [folder]
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import psutil  # noqa: E402

from sieve_player import catalogue, theme  # noqa: E402
from sieve_player.catalogue import CLASSES, Log, alike, needs, size, store_name  # noqa: E402
from sieve_player.dev.simulations import ROW, ROWS, H, W, _Run  # noqa: E402
from sieve_player.dev.timeview import SMALLEST, GuiPanel, MachinePanel, Problems, Stack, StoresPanel, Table, Turns, Window  # noqa: E402
from sieve_player.graph import Event  # noqa: E402
from sieve_player.ledger import Ledger, quantile, saved  # noqa: E402
from sieve_player.trace import FIELDS  # noqa: E402
from sieve_player.theme import LEVEL  # noqa: E402

out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
checks = {}
app = QApplication.instance() or QApplication([])
theme.install_font(app)


# The waits class is left out of the window's log here: on walks of a quarter second the tools' wall less
# their CPU is a tick's noise, and the monitor's own paint beside it was sighted in some runs and not others.
FAULTS = {k: v for k, v in CLASSES.items() if k != "waits"}


def part(win, kind):
    return next(p for p in win.parts if isinstance(p, kind))


def turn(win):
    for _ in range(3):
        QApplication.processEvents()
    win.refresh()
    QApplication.processEvents()


with tempfile.TemporaryDirectory() as tmp, _Run(tmp, memo_bytes=ROWS * ROW * 2, cache_bytes=8 * ROW * 3) as r:
    r.tools["work"].far, r.tools["pile"].ms = ROWS // 2, 0.1
    win = Window(r)
    win.resize(1280, 860)
    win.show()
    turn(win)       # its first layout and paint before the walk, as a window already open has them behind it
    win.log = Log(FAULTS)
    r.walk()
    r.walk()
    turn(win)
    problems, table, stores, gui = (part(win, k) for k in (Problems, Table, StoresPanel, GuiPanel))
    lines = [problems.lines.said(e) for e in problems.lines.entries]
    print(problems.head.text())
    print("\n".join("  " + " | ".join(ln) for ln in lines))
    print(" ", problems.foot.text())
    costs = [e.problem.ms_row for e in problems.lines.entries]
    checks["three problems lead, a line each, the costliest first"] = (
        len(lines) >= 3 and costs == sorted(costs, reverse=True) and all(all(ln) for ln in lines)
        and {e.problem.kind for e in problems.lines.entries} >= {"thrash", "seeks", "grows"} and problems.all.text() == f"Copy all {len(lines)}")
    checks["the classes that found nothing are one line under them"] = "checked and quiet: " in problems.foot.text()
    if out is not None:
        win.grab().save(str(out / "three.png"))

    print("the table:")
    print("\n".join("  " + " | ".join(ln) for ln in table.lines))
    marks = {}
    for i, e in enumerate(problems.lines.entries):
        QTest.mouseClick(problems.lines, Qt.MouseButton.LeftButton, pos=QPoint(200, int((i + 0.5) * problems.lines.H)))
        QApplication.processEvents()
        key = (e.problem.kind, e.problem.subject)
        marks[key] = (win.picked, set(table.marked), set(part(win, Stack).marked), stores.outlined, gui.outlined,
                      [said for _, said in win.time.marks], [t for t, _ in win.time.marks] == [e.first])
        print(f"picked {key}: table and stack {sorted(table.marked)}, stores outlined {stores.outlined}, flag {marks[key][5]}")
    checks["a press on a line picks it: its nodes marked in the table and the stack, its first sighting the one flag"] = all(
        m[0] == k and m[1] == m[2] == set(win.log.entries[k].problem.nodes) and m[5] == [f"first seen: {k[0]} {k[1]}"] and m[6]
        for k, m in marks.items())
    checks["the stores' panel is outlined for a store's problem alone, the interface thread's for none of these"] = all(
        m[3] == (k[0] == "thrash") and not m[4] for k, m in marks.items())
    seeks = next(k for k in marks if k[0] == "seeks")
    win.pick(seeks)
    QApplication.processEvents()
    at = [n for n, *_ in table.lines].index(seeks[1]) + 1
    row = table.rect().adjusted(0, theme.PAD + at * table.LINE, 0, 0)
    row.setHeight(table.LINE)
    drawn = [table.grab(row).toImage()]
    for kind, subject in (("grows", "pile"), ("thrash", "memo")):
        win.pick((kind, subject))
        QApplication.processEvents()
        drawn.append(table.grab(row).toImage())
    checks["a marked node's row is drawn marked in the table, and plain when another is picked"] = drawn[0] != drawn[1] == drawn[2]
    flag = win.time.grab().toImage()
    axis = win.time.axis()
    x = int(axis.x(int(win.log.entries[win.picked].first // axis.seconds)))
    checks["the flag is drawn on the axis at the first sighting"] = flag.pixelColor(x + 1, win.time.height() - win.time.RULER + 1) == LEVEL

    one = win.copy([seeks])
    both = win.copy()
    print(both)
    path = both.rsplit("HISTORY  ", 1)[1].strip()
    back, more = saved(path)
    checks["the copy of all is one block, the problems numbered, the shared parts once, the history's file holding the document"] = (
        QApplication.clipboard().text() == both and all(both.count(label) == 1 for label in ("WALK ", "BEFORE ", "PLAN ", "ROW ", "MACHINE ", "GUI ", "STORES ", "VIDEO ", "HISTORY "))
        and all(f"\n{i}  " in both for i in range(1, len(lines) + 1)) and more["document"]["nodes"] and back.view().walks)
    checks["the copy of one is the same block with one"] = one.splitlines()[1].startswith("1 problem,") and "\n2  " not in one and "WALK " in one
    for written in {path, one.rsplit("HISTORY  ", 1)[1].strip()}:       # one file when both copies fell in a second
        os.remove(written)

    win.pause.click()
    QApplication.processEvents()
    walks = len(win.view.walks)
    before = [w.grab().toImage() for w in (problems, table, win.time, stores)]
    r.walk(ROWS // 4, ROWS // 2)
    turn(win)
    same = before == [w.grab().toImage() for w in (problems, table, win.time, stores)]
    print("paused:", win.status.text(), "; the window's walks", len(win.view.walks), "the ledger's", len(r.ledger.view().walks))
    checks["paused it draws what it drew and says how far behind, the ledger's walks grown"] = (
        same and len(win.view.walks) == walks < len(r.ledger.view().walks) and win.status.text().startswith("paused · showing ")
        and win.pause.text() == "Resume")
    win.pause.click()
    turn(win)
    checks["resumed it reads them"] = len(win.view.walks) > walks and win.pause.text() == "Pause" and not win.status.text()
    win.time.PX = 300       # so few columns that this run's seconds are more than the axis holds, and there is somewhere to scroll back to
    win.time.scroll(0.5)
    turn(win)
    checks["and the axis scrolled back is the same holding"] = win.pause.text() == "Resume" and win.status.text().startswith("paused")
    win.pause.click()
    win.time.PX = 3

    win.resize(*SMALLEST)
    turn(win)
    if out is not None:
        win.grab().save(str(out / "smallest.png"))
    p = problems.lines.entries[0].problem
    print(f"at {win.width()}x{win.height()}:", problems.head.text(), "|", problems.all.text(), "| tracks", [type(t).__name__ for t, _ in win.time.rects()])
    checks["small, it is the rate, the costliest's sentence and target, how many more, the copy of all and the stack"] = (
        win.figure.isVisible() and problems.head.text() == f"{p.says} · {p.target} · and {len(lines) - 1} more" and problems.all.isVisible()
        and [type(t).__name__ for t, _ in win.time.rects()] == ["Stack"]
        and not any(w.isVisible() for w in (problems.lines, problems.foot, table, stores, gui, win.pause, win.history, win.full)))
    win.close()

led = Ledger()
led.event(Event(**{f: None for f in FIELDS} | {"kind": "begin", "row": 0, "length": 100, "t": -1.0, "ms": 0.0, "cpu_ms": 0.0, "bytes": 0,
                                                "thread": "worker", "lane": "window"}))
for i, ms in enumerate([1.0] * 98 + [50.0] * 2):
    led.event(Event(**{f: None for f in FIELDS} | {"kind": "run", "node": "a", "row": i, "t": float(i), "ms": ms, "cpu_ms": ms, "bytes": 0,
                                                    "thread": "worker", "lane": "window", "shape": (48, 64)}))
led.event(Event(**{f: None for f in FIELDS} | {"kind": "progress", "row": 100, "length": 100, "t": 100.0, "ms": 0.0, "cpu_ms": 0.0,
                                                "bytes": 0, "thread": "worker", "lane": "window"}))
sample = {"memory": [1, 2, 4], "cores": [0.5, 1.0, 8], "disk": [1.0, 2.0, 0.5], "gpu": None, "faults": 3.0}
led.sample("machine", sample, 50.0)
fed = led.view()
node = fed.walks[0].nodes["a"]
half, most = quantile(node.bins["run"], 0.5), quantile(node.bins["run"], 0.99)
print(f"98 runs of 1 ms and 2 of 50: the median reads {half:.3f} ms and the 99th percentile {most:.2f}; the shape kept {node.shape}")
checks["the ledger keeps a node's ms a run in bins: the median and the 99th percentile of two known costs, each within a twentieth"] = (
    abs(half - 1.0) < 0.05 and abs(most - 50.0) < 2.5 and sum(node.bins["run"]) == 100 and node.shape == [48, 64])
checks["a machine sample fed is in its bucket, and no other's"] = (
    fed.buckets[int(50.0 // fed.width) - fed.first].machine == sample and sum(bool(b.machine) for b in fed.buckets) == 1)

with tempfile.TemporaryDirectory() as tmp, _Run(tmp, cache_bytes=8 * ROW * 3, sample=0.1) as r:
    events, emit = [], r.graph.on_event
    r.graph.on_event = lambda ev: (events.append(ev), emit(ev))
    win = Window(r)
    win.resize(1280, 860)
    win.show()
    turn(win)
    win.log = Log(FAULTS)
    r.wait(lambda: any(b.machine for b in r.ledger.view().buckets), "the machine's first sample")
    r.walk()
    turn(win)
    shapes = {(ev.node, ev.kind): ev.shape for ev in events if ev.shape is not None}
    print("the shapes on the events:", shapes)
    checks["the stream carries the shape of what a span read or made: a decode's frame, a run's result, a fold's plane"] = (
        shapes[("video", "decode")] == (H, W, 3) and shapes[("gray", "run")] == shapes[("gray", "fold")] == (H, W)
        and all(ev.shape is None for ev in events if ev.kind in ("step", "progress", "sync")))

    table, panel = part(win, Table), part(win, MachinePanel)
    w = win.walk
    print("the table:")
    print("\n".join("  " + " | ".join(ln) for ln in table.lines))
    reads = {n: f["reads"] for n, f in w.plan["nodes"].items()}
    right = {}
    for nid, ms, run, per, by, free in table.lines[:-1]:
        x = w.nodes[nid]
        total = sum(v[1] for v in x.runs.values())
        kind, demand, asked = max(x.runs, key=lambda k: x.runs[k][1])
        frame = w.plan["nodes"][nid]["kind"] == "frame"       # a chain node reads no plane
        px = {"run": frame and sum(H * W for src in reads[nid].values() if src), "decode": H * W, "fold": H * W}.get(kind)
        spent = sum(v[1] for n in w.nodes.values() for v in n.runs.values()) + w.unprobed
        right[nid] = (ms == f"{total / w.done:.2f}"
                      and run == f"{quantile(x.bins[kind], 0.5):.2f} – {quantile(x.bins[kind], 0.99):.2f}"
                      and per == ("-" if not px else f"{quantile(x.bins[kind], 0.5) / (px / 1e6):.2f}")
                      and by == {"walk": "the walk", "fold": f"fold of {asked}"}[demand]
                      and free == f"{win.rate * spent / (spent - total):.1f}×")
    print("each column against the walk's record:", right)
    checks["the table is a row a node in walk order, each column the ledger's: ms a row, median and 99th percentile, ms per megapixel, what asked, the rate were it free"] = (
        [ln[0] for ln in table.lines] == ["video", "gray", "work", "bake", "edge", "mean", "pile", "unprobed"] and all(right.values())
        and table.lines[5][3] == table.lines[6][3] == "-")      # the chain reads no plane

    tracks = [type(t).__name__ for t in win.time.tracks]
    stack = part(win, Stack)
    rect = next(rc for t, rc in win.time.rects() if t is stack)
    segs = stack.segments(win.time.axis(), win.time.shown)
    image = win.time.grab().toImage()
    print("the default's tracks:", tracks, "; the walks over the stack:", [stack.label(sw) for _, _, sw in segs])
    checks["the time view's default is the worker's stack, each walk a labelled segment over it, the machine and the lateness under it"] = (
        tracks == ["Stack", "Load", "Late"] and [type(t).__name__ for t, _ in win.time.rects()] == tracks
        and [sw.t0 for _, _, sw in segs] == [sw.t0 for sw in win.view.walks if sw.done] and all(stack.label(sw).startswith("window · rows 0..63 · ") for _, _, sw in segs)
        and all(image.pixelColor(round(x0), int(rect.top()) + 2) == theme.qgray(theme.layer(3)) for x0, _, _ in segs))
    win.add(Turns())
    checks["and another track is added to it"] = [type(t).__name__ for t, _ in win.time.rects()] == [*tracks, "Turns"]
    win.time.tracks.pop()
    win.parts.pop()

    r.fresh()
    r.walk()
    turn(win)
    mem, mine = psutil.virtual_memory(), psutil.Process().memory_info().rss
    lines = {ln[0]: ln for ln in panel.lines}
    print("the machine's panel:", panel.says)
    print("\n".join(f"  {ln[0]}: {ln[1]} | {ln[3]}" for ln in panel.lines))
    print(f"the OS's own: {size(mem.total - mem.available)} of {size(mem.total)} in use, SIEVE {size(mine)}, {psutil.cpu_count()} cores")
    samples = [b.machine for b in win.view.buckets if b.machine]
    print(f"{len(samples)} samples, the last:", samples[-1])
    rss = max(m["memory"][0] for m in samples)
    checks["the machine is sampled into the ledger: memory, cores, disk and the hard faults, each SIEVE's and everything else's against the whole"] = (
        len(samples) >= 2 and all(m["memory"][2] == mem.total and m["cores"][2] == psutil.cpu_count() and len(m["disk"]) == 3
                                 and 0 <= m["cores"][0] <= m["cores"][0] + m["cores"][1] <= m["cores"][2] for m in samples)
        and (sys.platform != "win32" or all(m["faults"] is not None and m["disk"][2] is not None for m in samples)))
    checks["the panel's memory is the OS's own within a tenth, and SIEVE's is said by what holds it, the stores and the walk's stack"] = (
        lines["memory"][1].endswith(f"of {size(mem.total)}") and abs(rss - mine) < 0.1 * mine
        and abs(sum(samples[-1]["memory"][:2]) - (mem.total - mem.available)) < 0.1 * mem.total
        and all(held in lines["memory"][3] for held in ("SIEVE ", "memo ", "video cache ", "hard faults a second"))
        and "window stack" in {store_name(s, win.view) for b in win.view.buckets for s in b.stores})
    like = alike(win.view, win.walk)
    checks["the panel says none is tight, and shows the spread of the walks under the plan now walked"] = (
        panel.says == "No resource of the machine's is tight." and len(like) == 2
        and lines["2 walks alike"][1] == f"{min(like):.2f} – {max(like):.2f} ms a row" and len(lines["2 walks alike"][2]) == 2)
    catalogue.MEMORY = 0.01
    win._show()
    print("with memory tight at a hundredth in use:", panel.says)
    checks["and with memory's limit set low, that memory is what is tight"] = (
        panel.says.startswith("Memory is what is tight: memory ") and {ln[0]: ln[4] for ln in panel.lines}["memory"])
    catalogue.MEMORY = 0.9

    r.tools["work"].far, r.tools["pile"].ms = ROWS // 2, 0.1
    r.walk(ask=r.change("gray", k=1))
    turn(win)
    block = win.copy()
    print(block)
    two = [e for e in win.log.ordered() if e.holds][:2]
    checks["a copy of two problems is one block, each part once, the machine's lines and the table's columns among them"] = (
        len(two) == 2 and all(block.count(label) == 1 for label in ("\nWALK ", "\nBEFORE ", "\nPLAN ", "\nROW ", "\nMACHINE ", "\nGUI ", "\nSTORES ", "\nVIDEO ", "\nHISTORY ",
                                                                    "p50", "ms/MP", "\n         memory ", "\n         cores ", "\n         disk "))
        and all(block.count(f"\n{i}  {e.problem.kind} · {e.problem.subject} · ") == 1 and block.count(e.problem.says) >= 1 for i, e in enumerate(two, 1))
        and block.count("   from  ") == block.count("   repro ") == len([e for e in win.log.ordered() if e.holds]))
    os.remove(block.rsplit("HISTORY  ", 1)[1].strip())
    if out is not None:
        turn(win)
        win.grab().save(str(out / "machine.png"))
    win.close()

with tempfile.TemporaryDirectory() as tmp:
    seen, discards = [], []     # (rows done, the memo's need) at each row until the first discard, and the rows done at it
    with _Run(tmp, memo_bytes=ROWS * ROW * 2) as r:
        emit = r.graph.on_event

        def event(ev):
            emit(ev)
            if ev.kind == "evict" and not discards:
                discards.append(seen[-1][0] if seen else 0)
            elif ev.kind == "progress" and ev.lane == "window" and not discards:
                v = r.ledger.view()
                seen.append((ev.row, needs(v, v.walks[-1]).get("memo")))
        r.graph.on_event = event
        r.walk()
        limit = r.graph.memo.limit
    os.makedirs(os.path.join(tmp, "whole"))
    with _Run(os.path.join(tmp, "whole")) as r:
        r.walk()
        whole = r.graph.memo.bytes
    print(f"the memo holds {limit} bytes; its first discard came after row {discards[0]} of {ROWS}")
    print("the need read before it, by rows done:", ", ".join(f"{done}: {need:.0f}" for done, need in seen[:6]))
    print(f"an unbounded memo held {whole} bytes after the same walk")
    checks["a window that does not fit says so before the store discards anything"] = (
        bool(seen) and all(need and need > limit for _, need in seen) and 0 < discards[0] < ROWS)
    checks["and the need is what an unbounded memo then holds, within a twentieth"] = bool(seen) and abs(seen[0][1] - whole) < 0.05 * whole

for what, ok in checks.items():
    print(f"{'ok ' if ok else 'NOT'}  {what}")
sys.exit(0 if all(checks.values()) else 1)
