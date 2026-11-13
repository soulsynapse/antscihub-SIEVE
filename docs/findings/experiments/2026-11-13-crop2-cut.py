"""crop2 on the crossings clip, offscreen: the region's params arrive over the wire, a choice on the
region moves the cut served, and Cut's clips are the source's pixels at each rect, a frame for a frame:
equal when lossless, and how far off and how much smaller at standard. The bar's values while cutting are printed.

    .venv/Scripts/python.exe docs/findings/experiments/2026-11-13-crop2-cut.py
"""
import json
import os
import shutil
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document as D  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402
from tools import crop2, file, region  # noqa: E402

VIDEO = os.path.join(ROOT, "video-tests", "00000_168-178.mp4")
GEOMETRY = os.path.join(ROOT, "video-tests", "00000_168-178.shapes.geometry.json")
ROWS = (0, 300, 589)


def pump(until, timeout=40.0):
    t = time.perf_counter()
    while not until() and time.perf_counter() - t < timeout:
        QApplication.processEvents()
        time.sleep(0.01)
    assert until()


def frame(path, row):
    cap = cv2.VideoCapture(path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, row)
    ok, f = cap.read()
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    assert ok
    return f, n


def main():
    QApplication.instance() or QApplication([])
    work = tempfile.mkdtemp()
    video = shutil.copy(VIDEO, os.path.join(work, "clip.mp4"))
    shutil.copy(GEOMETRY, os.path.join(work, "geometry.json"))
    tools = [file, region, crop2]
    doc = D.from_tools([region, crop2], video)
    doc.add_node("file", params={**file.DEFAULTS, "pattern": "geometry.json"})
    doc.connect("file", "region", "geometry")
    doc.connect("video", "crop2")
    doc.connect("region", "crop2", "regions")
    doc.display = "crop2"
    D.save(doc, os.path.join(work, "doc.json"))
    win = PlayerWindow(os.path.join(work, "doc.json"), "t", tools)
    held = win.doc.node("crop2").params
    names = [s["name"] for s in held["shapes"]]
    print("arrived over the wire:", held["plate"], names, repr(held["choice"]))
    assert names and held["plate"] == [1080, 1920]

    def shown():
        p = win.display._pix
        return None if p is None else (p.height(), p.width())

    def size():
        y0, y1, x0, x1 = crop2.served(win.doc.node("crop2").params)
        return y1 - y0, x1 - x0

    pump(lambda: shown() == size())
    print("served, none chosen:", shown())
    for name in names:
        win.pane.widget("region").set_params({"choice": name})
        assert win.doc.node("crop2").params["choice"] == name
        pump(lambda: shown() == size())
        print(f"served, {name} chosen on the region:", shown())

    card = win.pane.widget("crop2")
    folder = crop2.folder_for(video)
    for quality in crop2.QUALITIES:
        card.set_params({"quality": quality})
        seen, texts = set(), []
        t = time.perf_counter()
        card.button.click()
        pump(lambda: (seen.add(card.bar.value()), texts.append(card.status.text()), card.cut is None)[-1])
        print(f"{quality}: cut in {time.perf_counter() - t:.1f} s; the bar read {sorted(seen)[:6]}.. of {card.bar.maximum()}")
        print("  mid-cut:", next((x for x in texts if "left" in x), "no estimate seen"))
        print("  after:", card.status.text())
        with open(os.path.join(folder, "crops.json"), encoding="utf-8") as f:
            said = json.load(f)
        assert said["quality"] == quality
        for c in said["crops"]:
            path = os.path.join(folder, c["file"])
            worst = 0
            for row in ROWS:
                src, n = frame(video, row)
                got, m = frame(path, row)
                want = src[c["y"]:c["y"] + c["h"], c["x"]:c["x"] + c["w"]]
                assert m == n and got.shape == want.shape, (c["name"], m, n, got.shape, want.shape)
                worst = max(worst, int(np.abs(got.astype(int) - want.astype(int)).max()))
            assert worst == 0 or quality != "lossless", (c["name"], worst)
            print(f"  {c['name']}: {c['w']}x{c['h']} at {c['x']}, {c['y']}, {m} frames, {os.path.getsize(path) / 1e6:.1f} MB, "
                  f"worst pixel off by {worst} at rows {ROWS}")
    win.close()
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
