"""A csv written of a clip and of a copy of it under another name: the key each node is planned
under, and the key line each file carries.
Run: .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-17-a-csv-of-a-clip-and-of-its-copy.py video-tests/03c2012ed6e61417.mp4"""
import os
import shutil
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.getcwd())

from sieve_player import document  # noqa: E402
from sieve_player.decoder import footage_print  # noqa: E402
from sieve_player.plan import base_key, plan  # noqa: E402
from tools import csv, gray, motion, reduce  # noqa: E402


def line_of(video, folder):
    tools = {t.NAME: t for t in (gray, motion, reduce, csv)}
    doc = document.from_tools(list(tools.values()), video)
    key = plan(doc, tools, base_key(footage_print(video), document.video_output(doc))).entries["csv"].key
    out = os.path.join(folder, os.path.basename(csv.default_name(video, 0, 3)))
    csv.write(out, {"signal": np.zeros(3, np.float32), "key": key}, 0, 30.0, video)
    with open(out, encoding="utf-8") as f:
        return f.readline().strip()


def main(clip):
    with tempfile.TemporaryDirectory() as folder:
        copy = os.path.join(folder, "another name.mp4")
        shutil.copyfile(clip, copy)
        a, b = line_of(clip, folder), line_of(copy, folder)
    print(a)
    print(b)
    field = lambda line, name: line.split(f"{name}=")[1].split(" ")[0]
    print("one key:", field(a, "key") == field(b, "key"), " one print:", field(a, "footage") == field(b, "footage"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
