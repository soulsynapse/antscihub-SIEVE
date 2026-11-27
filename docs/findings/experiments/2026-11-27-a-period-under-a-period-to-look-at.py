"""Writes a clip and a document to look at a `period` under a `period` in the player's window.

The clip is a minute of flat gray frames: bright for two seconds of every four, and while bright
alternating half a second very bright and half a second less so. `gate`, a banded `reduce`, cuts
`period` into the two-second stretches; `gate2`, banded higher and below `period`, cuts `inner`
into the half seconds inside each; `below` and `smooth` read `inner`. Opens no window.

Run: .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-27-a-period-under-a-period-to-look-at.py [folder]
`folder` is where the two files go, video-tests/nested-demo with none. Then
.venv/Scripts/python.exe -m sieve_player <folder>/doc.json
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from sieve_player import document as D  # noqa: E402

FPS, SECONDS = 30, 60
home = Path(sys.argv[1] if len(sys.argv) > 1 else "video-tests/nested-demo").resolve()
home.mkdir(parents=True, exist_ok=True)

wr = cv2.VideoWriter(str(home / "v.avi"), cv2.VideoWriter_fourcc(*"MJPG"), FPS, (320, 240))
for r in range(FPS * SECONDS):
    t = r / FPS
    wr.write(np.full((240, 320, 3), 20 if t % 4 >= 2 else 230 if t % 1 < 0.5 else 150, np.uint8))
wr.release()

doc = D.Document(video=str(home / "v.avi"))
doc.add_node(D.VIDEO_TOOL)
for nid, tool, src, into in (("gray", "gray", D.VIDEO_TOOL, None), ("gate", "reduce", "gray", None),
                             ("period", "period", "gray", None), ("period", None, "gate", "gate"),
                             ("gate2", "reduce", "period", None), ("inner", "period", "period", None), ("inner", None, "gate2", "gate"),
                             ("below", "reduce", "inner", None), ("smooth", "smooth", "below", None)):
    if tool is not None:
        doc.add_node(tool, (220.0 * (len(doc.nodes) % 3), 110.0 * (len(doc.nodes) // 3)), None, nid)
    doc.connect(src, nid, *([into] if into else []))
doc.node("gate").band = (100.0, 255.0)
doc.node("gate2").band = (200.0, 255.0)
D.save(doc, home / "doc.json")
print(home / "doc.json")
