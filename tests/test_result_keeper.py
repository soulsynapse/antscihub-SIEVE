"""A bare walk's frame-node rows kept between walks: what a second walk reads back, and what makes it make rows again."""
import gc
import json
import os
import pickle
import random

import cv2
import numpy as np
import pytest

from sieve_player import bare, decoder, registry
from sieve_player import document as D
from sieve_player.registry import discover
from sieve_player.result_keeper import FOLDER_ENV
from sieve_player.result_store import ENTRIES, PARTS, Address, Folder, Refused, Store
from tests.stepping import same

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
ROWS = 300      # a whole chunk and part of another


@pytest.fixture
def clip(tmp_path, monkeypatch):
    """(walk(params) -> (results, detect's runs), the keeper's folder, row -> detect's table at its
    last run there): a bare walk in-process over a synthetic clip of squares moving on a dark
    floor, gray, threshold, detect and count."""
    monkeypatch.setenv(FOLDER_ENV, str(tmp_path / "results"))
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

    def walk(**params):
        doc = D.from_tools([tools[n] for n in ("gray", "threshold", "detect", "count")], video)
        next(n for n in doc.nodes if n.tool == "detect").params.update(params)
        job, out = tmp_path / "job.json", str(tmp_path / "out.pickle")
        job.write_text(json.dumps(bare.job(doc, video, {"detect": tools["detect"]}, out)), encoding="utf-8")
        runs[0] = 0
        assert bare.main(str(job)) == 0
        gc.collect()        # the walk's decoder, held in the Graph's cycles, lets the file go
        with open(out, "rb") as f:
            return pickle.load(f)[0], runs[0]
    return walk, tmp_path / "results", made


def same_results(a, b):
    return a.keys() == b.keys() and all(a[k].keys() == b[k].keys() and all(same(a[k][f], b[k][f]) for f in a[k]) for k in a)


def test_a_second_walk_reads_detect_back_and_gives_the_same_results(clip):
    walk, folder, tables = clip
    first, made = walk()
    second, again = walk()
    assert made == ROWS and again == 0 and same_results(first, second)
    disk = Folder(str(folder))
    kept = {r: v for n in disk.names(ENTRIES) if "rows/" in n for r, v in disk.read(n)[0].items()}
    assert kept.keys() == tables.keys() and all(same(kept[r], tables[r]) and kept[r].dtype.metadata for r in kept)


def test_a_changed_param_or_code_print_makes_rows_again(clip, monkeypatch):
    walk, _, _ = clip
    walk()
    assert walk(min_area=5)[1] == ROWS
    detect = next(t for t in registry._IMPORTED.values() if t[0].__name__.endswith(".detect"))[0]
    monkeypatch.setitem(registry._IMPORTED, id(detect), (detect, "changed"))
    assert walk(min_area=5)[1] == ROWS and walk(min_area=5)[1] == 0


def test_footage_its_sampled_print_tells_apart_makes_rows_again(clip, tmp_path):
    walk, _, _ = clip
    before = decoder.footage_print(tmp_path / "v.avi")
    walk()
    with open(tmp_path / "v.avi", "ab") as f:
        f.write(b"\0")
    assert decoder.footage_print(tmp_path / "v.avi") != before
    assert walk()[1] == ROWS and walk()[1] == 0


def test_a_chunk_cut_short_is_made_again_and_nothing_raises(clip):
    walk, folder, _ = clip
    first, _ = walk()
    chunks = [os.path.join(at, f) for at, _, fs in os.walk(folder / "entries") if at.endswith("rows") for f in fs]
    assert len(chunks) == 2
    with open(chunks[0], "r+b") as f:
        f.truncate(os.path.getsize(chunks[0]) // 2)
    second, made = walk()
    assert 0 < made < ROWS and same_results(first, second) and walk()[1] == 0


def test_two_stores_over_one_folder_read_back_only_what_was_put(tmp_path):
    """docs/playground/sim/folder_check.py's seeded doings of two stores over one folder against a
    dict of what each address holds: a get answers that or nothing, a checkpoint loses no entry it
    names, and the entries stay near the budget."""
    rng, clock, truth, marks, budget = random.Random(0), [1e6], {}, {}, 200_000

    def opened(writer):
        return Store(Folder(str(tmp_path), writer, now=lambda: clock[0], wait=lambda s: None), 60_000, budget, writer, worth=False)
    stores = [opened("a"), opened("b")]
    for step in range(300):
        clock[0] += rng.choice((0.1, 1, 90))
        store, address = rng.choice(stores), Address(f"k{rng.randrange(12)}", rng.randrange(6))
        does = rng.choice(("put", "put", "get", "get", "checkpoint", "release", "drop", "reopen", "tear", "part", "forget"))
        if does == "put":
            truth.setdefault(address, os.urandom(rng.randrange(100, 9000)))
            store.put(address, truth[address], len(truth[address]), cost=1.0)
        elif does == "get":
            got = store.get(address)
            assert got is None or got == truth.get(address), f"step {step}: {address} read back as another value"
        elif does == "checkpoint":
            named = rng.sample(sorted(truth), min(len(truth), 3))
            try:
                store.checkpoint(f"m{step}", {}, named, [len(truth[a]) for a in named],
                                 lambda a: store.put(a, truth[a], len(truth[a]), keep=True))
                marks[f"m{step}"] = named
            except Refused:
                pass
        elif does == "release" and marks:
            store.release_checkpoint(marks.popitem()[0])
        elif does == "drop":
            store.drop(address)
        elif does == "reopen":
            stores[rng.randrange(2)] = opened(rng.choice("ab") + str(step))
        elif does == "tear" and not any(address in n for n in marks.values()) and os.path.exists(path := tmp_path.joinpath(*address.name.split("/"))):
            with open(path, "r+b") as f:
                f.truncate(rng.randrange(0, max(1, os.path.getsize(path))))
            for s in stores:
                s.forget()
        elif does == "part":
            (tmp_path / PARTS).mkdir(exist_ok=True)
            (tmp_path / PARTS / f"crashed-{step}").write_bytes(os.urandom(5000))
        elif does == "forget":
            store.forget()
        assert all(stores[0].disk.read(a.name) is not None for n in marks.values() for a in n), f"step {step} ({does}): a checkpoint lost an entry"
        assert sum(p.stat().st_size for p in (tmp_path / ENTRIES).rglob("*") if p.is_file()) <= budget * 1.25 or not (tmp_path / ENTRIES).exists()
