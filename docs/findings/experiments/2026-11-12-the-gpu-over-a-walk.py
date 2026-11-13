"""Experiment behind docs/findings/2026-11-12-the-gpu-over-a-walk.md, the observation the GPU's fork in
docs/spec/monitor.md asks for: what OpenCV here is built with and what the plate's capture says of its own
acceleration, then this process's share of every GPU engine, sampled while video-tests/purb-settings.json
walks one window with every bake live, offscreen, so nothing paints; and beside it the share of any
player open on the machine, another process, whose painting is the other half of the fork.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-12-the-gpu-over-a-walk.py [rows] 2>NUL

The counters are machine._Counters' own, read raw: an instance is a process's use of one engine of one
adapter, and its name ends in the engine's type.
"""
import os
import sys
import threading
import time
from collections import defaultdict

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ROWS = int(sys.argv[1]) if len(sys.argv) > 1 else 1800
sys.path.insert(0, ROOT)

import cv2  # noqa: E402
import psutil  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player import machine  # noqa: E402
from sieve_player import store  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-settings.json")
PERIOD = 0.25
PLAYERS = [p.pid for p in psutil.process_iter(["cmdline"])
           if p.pid != os.getpid() and "sieve_player" in (p.info["cmdline"] or ())]     # python -m sieve_player


def built():
    info = cv2.getBuildInformation()
    keep = ("NVIDIA CUDA", "OpenCL:", "FFMPEG:", "DXVA", "D3D11", "Intel VA", "MFX", "Media Foundation")
    for ln in info.splitlines():
        if any(k in ln for k in keep):
            print("   " + ln.strip())
    print(f"   cuda devices {cv2.cuda.getCudaEnabledDeviceCount()}, "
          f"OpenCL have {cv2.ocl.haveOpenCL()} use {cv2.ocl.useOpenCL()}")


def sampler(stop, out):
    c = machine._Counters()
    mine = f"pid_{os.getpid()}_"
    theirs = tuple(f"pid_{p}_" for p in PLAYERS)
    while not stop.wait(PERIOD):
        got = c.read()["gpu"]
        if got is None:
            out.append(None)
            continue
        ours, all_, player = defaultdict(float), defaultdict(float), defaultdict(float)
        for name, v in got.items():
            kind = name.split("engtype_")[-1]
            all_[kind] += v
            if name.startswith(mine):
                ours[kind] += v
            if theirs and name.startswith(theirs):
                player[kind] += v
        out.append((dict(ours), dict(all_), dict(player)))
    c.close()


def walk(g, length):
    walked, series = [], []
    w = Worker(g)
    w.walked.connect(lambda d, n: walked.append((d, n)))
    w.seriesReady.connect(lambda r, s, fps: series.append(r))
    w.set_window(0, length)
    w.start()
    t = time.perf_counter()
    while not (walked and walked[-1][0] == walked[-1][1] and (series or not g.chain)):
        QApplication.processEvents()
        time.sleep(0.002)
        if time.perf_counter() - t > 900:
            sys.exit("the walk did not finish")
    w.stop()
    return time.perf_counter() - t


def main():
    QApplication.instance() or QApplication([])
    decmod.QUIET = True
    print("OpenCV", cv2.__version__)
    built()
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    doc = D.load(DOC, tools)
    for node in doc.nodes:
        if node.tool == "bake":
            node.mode = D.LIVE
    dec = Decoder(doc.video)
    cap = dec._cursors["walk"].cap
    print(f"   the plate's capture: backend {cap.getBackendName()}, "
          f"CAP_PROP_HW_ACCELERATION {cap.get(cv2.CAP_PROP_HW_ACCELERATION):.0f} (0 is none), "
          f"HW_DEVICE {cap.get(cv2.CAP_PROP_HW_DEVICE):.0f}, {dec.width}x{dec.height}")
    st = store.current()
    g = Graph(doc, dec, tools, open_bake=lambda bk, c: st.open_bake(bk, c))
    g.sync()
    n = min(ROWS, g.count)
    stop, samples = threading.Event(), []
    th = threading.Thread(target=sampler, args=(stop, samples), daemon=True)
    th.start()
    s = walk(g, n)
    stop.set()
    th.join()
    g.close()
    dec.close()
    print(f"\n{n} rows live in {s:.1f} s, {len(samples)} samples at {PERIOD} s")
    got = [x for x in samples if x is not None]
    if not got:
        print("   the GPU's counters were not read")
        return
    kinds = sorted({k for x in got for k in x[1]})
    print(f"   an open player beside this walk: pids {PLAYERS or 'none'}")
    print(f"   {'engine':16} {'walk max %':>11} {'walk mean %':>12} {'player max %':>13} {'player mean %':>14} {'all max %':>10} {'all mean %':>11}")
    for k in kinds:
        o, a, pl = ([x[i].get(k, 0.0) for x in got] for i in (0, 1, 2))
        print(f"   {k:16} {max(o):>11.2f} {sum(o) / len(o):>12.2f} {max(pl):>13.2f} {sum(pl) / len(pl):>14.2f} "
              f"{max(a):>10.2f} {sum(a) / len(a):>11.2f}")
    print(f"   samples in which the walk's process had an instance: {sum(1 for x in got if x[0])} of {len(got)}; "
          f"the player's: {sum(1 for x in got if x[2])}")


if __name__ == "__main__":
    main()
