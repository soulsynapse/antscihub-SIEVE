"""A cutting node's file: served only where the node reads the video node, under the key a document
opened on the file gives its video node; one piece of the plate a node; a cut file named by its key
and never written over, in the store; and region's answer off the store."""
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace as Tool

import pytest

from sieve_player import document as D
from sieve_player.decoder import Decoder, EndOfStream, footage_print
from sieve_player.graph import Graph
from sieve_player.plan import base_key, plan
from sieve_player.registry import defaults
from tests.test_crop import clip
from tests.test_graph import add, gray, same
from tools import _cutfile as C
from tools import region

cut = Tool(NAME="cut", KIND="frame", EXPECTS="bgr", PRODUCES="bgr", run=lambda frames, row, params: frames(row),
           cut_file=lambda video, footage, params: None)
both = Tool(NAME="both", KIND="frame", EXPECTS="gray", PRODUCES="gray", INPUTS={"other": "gray"},
            run=lambda frames, row, params: frames(row))
TOOLS = {t.NAME: t for t in (cut, gray, add, same, both)}
FILE = {"cut": ("piece.mp4", "print")}
SHAPES = [{"name": "nest", "polygon": [[10, 10], [30, 10], [30, 20], [10, 20]]}, {"name": "dish", "circle": [40, 30, 8]}]
MOVED = [{"name": "nest", "polygon": [[12, 10], [32, 10], [32, 20], [12, 20]]}, SHAPES[1]]
WRITES = "for p in sys.argv[1:]: open(p, 'wb').write(b'clip')"


def asker(files):
    """plan()'s cut_file over a table: what each node of `files` answers, whatever footage it is asked of."""
    return lambda nid, up: files.get(nid)


def params(choice="nest", shapes=SHAPES, **more):
    return {**defaults(region), "plate": [48, 64], "shapes": shapes, "choice": choice, **more}


def encoder(monkeypatch, code=WRITES):
    """A stand-in for ffmpeg: a process that runs `code` with the part files as its arguments."""
    monkeypatch.setattr(C, "command", lambda video, pieces, quality, progress:
                        [sys.executable, "-c", "import sys, time\n" + code, *(part for part, _ in pieces)])


def folder_of(video):
    """The store's folder for `video`'s footage, made."""
    folder = C.folder_for(video, footage_print(video))
    os.makedirs(folder)
    return Path(folder)


def ended(cut):
    while (said := cut.poll()) is None:
        time.sleep(0.01)
    return said


def test_a_served_node_and_all_after_it_are_keyed_as_the_document_opened_on_its_file():
    doc = D.from_tools([cut, gray, add])
    alone = plan(D.from_tools([gray, add]), TOOLS, base_key("print", "bgr"))
    served, live = plan(doc, TOOLS, "plate", asker(FILE)), plan(doc, TOOLS, "plate")
    assert served.entries["cut"].file == FILE["cut"] and served.entries["cut"].srcs == {"in": None} and served.entries["cut"].fed
    assert {n: served.entries[n].key for n in ("cut", "gray", "add")} == {"cut": alone.entries["video"].key, **{n: alone.entries[n].key for n in ("gray", "add")}}
    assert live.entries["cut"].file is None and live.entries["add"].key != served.entries["add"].key
    assert (served.entries["cut"].piece, served.entries["add"].piece, live.entries["add"].piece) == (None, "cut", "cut")
    doc.add_node("cut", id="inner")
    doc.connect("cut", "inner")
    inner = {"inner": ("inner.mp4", "inner print")}     # a cut of a served file is served; of a run it is not
    assert plan(doc, TOOLS, "plate", asker({**FILE, **inner})).entries["inner"].key == base_key("inner print", "bgr")
    assert plan(doc, TOOLS, "plate", asker(inner)).entries["inner"].file is None
    between = D.from_tools([same, cut, gray])       # the file is of the video, not of what a node between hands the cut
    between.nodes[1].tool, between.nodes[1].id = "pass", "pass"
    between.wires = [D.Wire("video", "pass"), D.Wire("pass", "cut"), D.Wire("cut", "gray")]
    through = Tool(**{**vars(cut), "NAME": "pass", "cut_file": None})
    assert plan(between, {**TOOLS, "pass": through}, "plate", asker(FILE)).entries["cut"].file is None


def test_a_node_whose_inputs_are_of_two_pieces_of_the_plate_is_not_fed_and_says_which():
    doc = D.from_tools([cut, gray])
    doc.add_node("gray", id="whole")
    doc.connect("video", "whole")
    doc.add_node("both")
    doc.connect("gray", "both")
    doc.connect("whole", "both", "other")
    doc.add_node("add")
    doc.connect("both", "add")
    for ask in (None, asker(FILE)):       # refused cut or uncut: what a node may read never follows whether a file is there
        e = plan(doc, TOOLS, "plate", ask).entries
        assert e["both"].standing == "reads across a cut: in is of cut, other of the plate" and not e["both"].fed
        assert not e["add"].fed and e["add"].standing == "in waits on both" and e["gray"].fed and e["whole"].fed


def test_a_graph_reads_a_served_nodes_rows_from_its_file_and_from_its_run_once_its_tool_answers_none(tmp_path):
    plate, piece = clip(tmp_path / "plate.avi"), clip(tmp_path / "piece.avi", n=4, h=24, w=32)
    asked, answer = [], [piece]
    cuts = Tool(**{**vars(cut), "cut_file": lambda video, footage, params: asked.append(video) or answer[0]})
    doc = D.from_tools([cuts, gray], plate)
    doc.add_node("cut", id="inner")
    doc.connect("cut", "inner")
    g = Graph(doc, Decoder(plate), {"cut": cuts, "gray": gray})
    try:
        assert sorted(asked) == sorted([plate, piece])      # the cut below a served one is asked of the served file
        assert g.compute("cut", 2).shape == (24, 32, 3) and g.compute("gray", 2).shape == (24, 32)
        assert (g.footage("gray"), g.footage("cut")) == (piece, plate) and g.readers.held(piece) is not None
        assert g.key("cut") == base_key(footage_print(piece), "bgr") != g.key("video")
        with pytest.raises(EndOfStream):
            g.compute("cut", 4)
        assert g.count == 4                                 # the served file's end is the plate's, which no read of the plate found
        answer[0] = None
        g.sync()
        assert g.compute("cut", 2).shape == (48, 64, 3) and g.footage("gray") == plate and g.entry("cut").file is None
        cuts.cut_file = lambda video, footage, params: 1 / 0
        g.sync()
        assert g.standing("cut").startswith("cut_file raised: ZeroDivisionError") and g.entry("cut").file is None

        def absent(video, footage, params):
            raise FileNotFoundError("nest is not cut")
        cuts.cut_file = absent                              # to serve a file and none there: the node does not run on the frame
        g.sync()
        assert g.standing("cut") == "nest is not cut" and not g.fed("cut") and g.compute("cut", 2) is None
        assert g.standing("gray") == "in waits on cut" and g.compute("gray", 2) is None
    finally:
        g.close()
        g.decoder.close()


def test_the_served_files_share_the_plates_cache_limit_and_the_one_read_latest_has_it(tmp_path):
    plate, files = clip(tmp_path / "plate.avi"), {n: clip(tmp_path / f"{n}.avi", n=4, h=24, w=32) for n in ("a", "b")}
    frame = 24 * 32 * 3
    tools = {n: Tool(**{**vars(cut), "NAME": n, "cut_file": lambda video, footage, params, n=n: files[n]}) for n in files}
    doc = D.from_tools([tools["a"]], plate)
    doc.add_node("b")
    doc.connect("video", "b")
    g = Graph(doc, Decoder(plate, cache_bytes=3 * frame), tools)
    try:
        held = lambda n: g.readers.held(files[n]).cache_bytes
        for row in range(3):
            g.compute("a", row)
        assert held("a") == 3 * frame
        for row in range(3):
            g.compute("b", row)
        assert held("b") == 3 * frame and held("a") == frame       # a frame stays whatever the limit
    finally:
        g.close()
        g.decoder.close()


def test_a_cut_files_key_is_of_its_footage_extent_and_recipe_and_reads_the_extents_kind_alone(monkeypatch):
    rect, rows, track = {"kind": "rect", "rect": [0, 8, 0, 8]}, {"kind": "rows", "rows": [0, 8]}, {"kind": "rect a row", "rects": [[0, 8, 0, 8]]}
    key = lambda extent, quality="standard", footage="print": C.key(footage, extent, C.recipe(quality))
    assert key(rect) == key(dict(reversed(rect.items()))) and len({key(rect), key(rows), key(track)}) == 3
    assert len({key(rect), key(rect, "lossless"), key(rect, footage="another")}) == 3
    was = key(rect)
    monkeypatch.setitem(C.ENCODE, "standard", (*C.ENCODE["standard"], "-tune", "grain"))
    assert key(rect) != was
    with pytest.raises(ValueError, match="kind"):
        key({"rect": [0, 8, 0, 8]})


def test_a_videos_cut_files_lie_under_its_print_and_a_cut_files_under_it_and_go_with_it(tmp_path, in_store, monkeypatch):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"plate")
    folder = folder_of(video)
    assert folder == in_store / footage_print(video)
    piece = folder / C.file_for("nest", "0123456789abcdef")
    below = Path(C.folder_for(piece, "the piece's print"))
    assert below == folder / "0123456789abcdef"                         # of a cut file, whatever its print
    below.mkdir()
    for path, said in ((piece, b"nest"), (below / C.file_for("ant", "fedcba9876543210"), b"ant"), (folder / C.file_for("dish", "0" * 16), b"dish"),
                       (folder / "notes.mp4", b"no cut file")):
        path.write_bytes(said)
    listed = [(str(piece), "nest-0123456789abcdef", 7)]
    assert C.unused(str(folder), [str(folder / C.file_for("dish", "0" * 16))]) == listed
    with monkeypatch.context() as m:        # what is cut of a clip will not go: the clip stays under its name, still listed
        m.setattr(C.shutil, "rmtree", lambda path: (_ for _ in ()).throw(OSError(13, "in use")))
        assert C.delete([str(piece)]) == [(str(piece), "in use")]
        assert C.unused(str(folder), [str(folder / C.file_for("dish", "0" * 16))]) == listed
    assert C.delete([str(piece)]) == [] and sorted(p.name for p in folder.iterdir()) == [C.file_for("dish", "0" * 16), "notes.mp4"]


def test_a_card_is_told_the_files_in_use_when_they_change_and_when_the_store_is_another():
    from PySide6.QtWidgets import QApplication

    from sieve_player.pane import Pane

    QApplication.instance() or QApplication([])
    pane, told = Pane({}), []
    pane.widgets["region"] = Tool(set_cut_files_in_use=told.append)
    for paths, again in ((["b", "a"], False), (["a", "b"], False), (["a", "b"], True), (["a"], False)):
        pane.set_cut_files_in_use(paths, again)
    assert told == [("a", "b"), ("a", "b"), ("a",)]


def test_a_cut_however_it_ends_leaves_every_path_that_was_there_as_it_was(tmp_path, monkeypatch):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"plate")
    folder = folder_of(video)
    rects = dict(region.crops(params()))
    found = [C.rect_piece(name, rect) for name, rect in rects.items()]
    keys = {name: C.rect_key(footage_print(video), rect, "standard") for name, rect in rects.items()}
    for name, said in ((C.file_for("nest", keys["nest"]), b"nest"), ("another.mp4", b"another")):
        (folder / name).write_bytes(said)
    held = lambda: {p.name: p.read_bytes() for p in folder.iterdir()}
    before = held()
    for code, end in (("sys.exit(3)", "ffmpeg exited 3: "), ("time.sleep(30)", "cancelled"), (WRITES, "")):
        encoder(monkeypatch, code)
        cut = C.Cut(str(video), found, "standard")
        assert [t[0] for t in cut.todo] == ["dish"]                 # nest's clip is there
        if end == "cancelled":
            with pytest.raises(ValueError, match="being cut"):      # a key a Cut is writing is no other Cut's to write
                C.Cut(str(video), found, "standard")
            cut.cancel()
        assert ended(cut) == end
        after = held()
        assert {n: after[n] for n in before} == before and not [n for n in after if C.PART in n]
    with monkeypatch.context() as m:    # another writer has both names as a Cut lands, unseen when it looks at the folder: its files stay
        m.setattr(C, "landed", lambda folder: {})
        assert ended(C.Cut(str(video), found, "standard")) == "" and held() == after
    dish = C.landed(str(folder))[keys["dish"]]
    assert set(after) - set(before) == {os.path.basename(dish), os.path.basename(dish) + C.SIDECAR}
    assert C.sidecar(dish)["bytes"] == 4 and C.sidecar(dish)["extent"] == C.rect_extent(rects["dish"]) and C.whole(dish)
    with pytest.raises(ValueError, match="nothing to cut"):
        C.Cut(str(video), found, "standard")


def test_a_cut_for_a_moved_shape_lands_while_two_nodes_read_their_clips_of_the_folder(tmp_path, monkeypatch):
    plate = clip(tmp_path / "plate.avi")
    folder = folder_of(plate)
    for name, (y0, y1, x0, x1) in region.crops(params()):
        made = clip(tmp_path / f"{name}.avi", n=4, h=y1 - y0, w=x1 - x0)
        os.rename(made, folder / C.file_for(name, C.rect_key(footage_print(plate), (y0, y1, x0, x1), "standard")))
    doc = D.from_tools([region], plate)
    doc.node("region").params = params("nest")
    doc.add_node("region", id="other", params=params("dish"))
    doc.connect("video", "other")
    g = Graph(doc, Decoder(plate), {"region": region})
    try:
        was = {n: g.entry(n).file[0] for n in ("region", "other")}
        said = {p: open(p, "rb").read() for p in was.values()}
        g.compute("region", 0), g.compute("other", 0)
        doc.node("region").params = params("nest", MOVED)
        g.sync()
        assert g.entry("region").file is None and g.entry("other").file[0] == was["other"]
        encoder(monkeypatch)
        assert ended(C.Cut(plate, [C.rect_piece(*crop) for crop in region.crops(params("nest", MOVED))], "standard")) == ""
        g.sync()
        now = g.entry("region").file[0]
        assert now not in was.values() and now in g.cut_files_in_use() and g.readers.held(was["other"]) is not None
        assert {p: open(p, "rb").read() for p in was.values()} == said
        doc.add_node("absent", id="between")
        doc.connect("video", "between"), doc.connect("between", "other")
        g.sync()
        assert g.entry("other").file is None and was["other"] in g.cut_files_named()     # named where it is not served
    finally:
        g.close()
        g.decoder.close()


def test_region_answers_the_clip_of_this_footage_at_the_chosen_shapes_rect_and_quality(tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"plate")
    folder = folder_of(video)
    print_ = footage_print(video)
    key = C.rect_key(print_, dict(region.crops(params()))["nest"], "standard")
    nest = folder / C.file_for("nest", key)
    nest.write_bytes(b"nest")
    ask = lambda footage=print_, **change: region.cut_file(str(video), footage, params(**change))
    assert ask() == str(nest) and region.cut_files(str(video), print_, params("")) == [str(nest)]
    assert ask(choice="") is None and ask(choice="no shape of the file") is None
    for change in ({"choice": "dish"}, {"shapes": MOVED}, {"quality": "lossless"}, {"footage": "another"}):
        with pytest.raises(FileNotFoundError, match="serve clip"):
            ask(**change)
    unserved = params(**{"serve clip": False})
    assert ask(**{"serve clip": False}) is None and region.cut_files(str(video), print_, unserved) == [str(nest)]
    sidecar = folder / (nest.name + C.SIDECAR)
    sidecar.write_text(json.dumps({"bytes": 4}), encoding="utf-8")
    assert ask() == str(nest)
    sidecar.write_text(json.dumps({"bytes": 9}), encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="not the size"):          # a clip of another size than landed
        ask()
    sidecar.unlink()
    os.rename(nest, folder / C.file_for("renamed", key))
    assert ask() == str(folder / C.file_for("renamed", key))            # the label names nothing
