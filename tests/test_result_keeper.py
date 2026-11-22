"""A frame node's small rows kept: what a bare walk hands back reaches a checkpoint and answers a player of it, and what an address tells apart."""
import gc
import json
import pickle
import shutil
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from sieve_player import bare, held, registry
from sieve_player import document as D
from sieve_player.decoder import Decoder
from sieve_player.graph import Graph
from sieve_player.registry import discover
from sieve_player.result_keeper import Keeper
from tests.stepping import same

ROOT = str(Path(__file__).resolve().parents[1] / "tools")
ROWS = 300      # a whole chunk and part of another


@pytest.fixture
def clip(tmp_path, monkeypatch):
    """(the clip, the tools, a list holding detect's runs, row -> detect's table at its last run
    there): a synthetic clip of squares moving on a dark floor, and detect counted."""
    video = str(tmp_path / "v.avi")
    w = cv2.VideoWriter(video, cv2.VideoWriter_fourcc(*"MJPG"), 30, (64, 48))
    for i in range(ROWS):
        f = np.full((48, 64, 3), 20, np.uint8)
        for k in range(1 + i % 3):
            f[5 + 12 * k:13 + 12 * k, (i + 9 * k) % 56:(i + 9 * k) % 56 + 8] = 220
        w.write(f)
    w.release()
    tools = {e.name: e.module for e in discover(ROOT) if e.ok}
    runs, made = [0], {}
    run = tools["detect"].run

    def counted(frames, row, params):
        runs[0] += 1
        made[row] = run(frames, row, params)
        return made[row]
    monkeypatch.setattr(tools["detect"], "run", counted)
    return video, tools, runs, made


def tables(tools, video, **params):
    doc = D.from_tools([tools[n] for n in ("gray", "threshold", "detect", "count")], video)
    next(n for n in doc.nodes if n.tool == "detect").params.update(params)
    return doc


def walked(doc, video, tools, keeper, runs, rows=range(ROWS)):
    """detect's rows over `rows` of a Graph of `doc` over `video` handed `keeper`, and detect's runs."""
    dec = Decoder(video)
    g = Graph(doc, dec, tools, keeper=keeper)
    g.sync()
    nid = next(n.id for n in doc.nodes if n.tool == "detect")
    runs[0] = 0
    try:
        return [g.compute(nid, r) for r in rows], runs[0]
    finally:
        g.close()
        dec.close()


def test_a_bare_walks_small_rows_reach_the_checkpoint_and_answer_a_player_of_it(clip, tmp_path):
    video, tools, runs, made = clip
    doc = tables(tools, video)
    job, out = tmp_path / "job.json", str(tmp_path / "out.pickle")
    job.write_text(json.dumps(bare.job(doc, video, {"detect": tools["detect"]}, out)), encoding="utf-8")
    assert bare.main(str(job)) == 0
    gc.collect()        # the walk's decoder, held in the Graph's cycles, lets the file go
    with open(out, "rb") as f:
        handed = pickle.load(f)[4]
    kept = {r: v for rows in handed.values() for r, v in rows.items()}
    assert kept.keys() == made.keys() and all(same(kept[r], made[r]) and kept[r].dtype.metadata for r in kept)   # detect's tables and no plane
    player = Keeper()
    player.take(handed)
    assert player.waiting()
    path = str(tmp_path / "doc.json.checkpoint")
    held.File(path).write([], lambda had: player.kept(had, short=True))
    assert not player.waiting()
    back = held.File(path)
    back.load()
    colleague = Keeper()
    colleague.lend(back.chunks)
    got, ran = walked(doc, video, tools, colleague, runs)
    assert ran == 0 and all(same(g, made[r]) for r, g in enumerate(got))


def test_an_address_tells_apart_params_code_footage_and_cut_rows(clip, tmp_path, monkeypatch):
    video, tools, runs, _ = clip
    keeper, some = Keeper(), range(10)
    assert walked(tables(tools, video), video, tools, keeper, runs, some)[1] == 10
    copy = str(tmp_path / "copy.avi")
    shutil.copy(video, copy)
    assert walked(tables(tools, copy), copy, tools, keeper, runs, some)[1] == 0     # another path to the same bytes
    assert walked(tables(tools, video, min_area=5), video, tools, keeper, runs, some)[1] == 10
    with open(copy, "ab") as f:
        f.write(b"\0")
    assert walked(tables(tools, copy), copy, tools, keeper, runs, some)[1] == 10
    detect = next(t for t in registry._IMPORTED.values() if t[0].__name__.endswith(".detect"))[0]
    monkeypatch.setitem(registry._IMPORTED, id(detect), (detect, "changed"))
    assert walked(tables(tools, video), video, tools, keeper, runs, some)[1] == 10

    e = SimpleNamespace(kind="frame", static=False, file=None, steps=False, raw_key="k", reach=(0, 0))
    within = SimpleNamespace(extent=SimpleNamespace(rows=(0, 8)))
    keeper.made(e, 3, within, np.float64(1.5))
    keeper.made(e, 4, within, np.zeros((2, 2)))      # a plane: never kept
    assert keeper.ask(e, 3, within) == 1.5 and keeper.ask(e, 4, within) is None
    assert keeper.ask(e, 3, SimpleNamespace(extent=SimpleNamespace(rows=(0, 16)))) is None
    assert keeper.ask(e, 3, SimpleNamespace(extent=SimpleNamespace(rows=None))) is None
