"""A cutting node's file: served only where the node reads the video node, under the key a document
opened on the file gives its video node; one piece of the plate a node; and region's answer off its record."""
import json
import os
from types import SimpleNamespace as Tool

from sieve_player import document as D
from sieve_player.decoder import Decoder, footage_print
from sieve_player.graph import Graph
from sieve_player.plan import base_key, plan
from tests.test_crop import clip
from tests.test_graph import add, gray, same
from tools import region

cut = Tool(NAME="cut", KIND="frame", EXPECTS="bgr", PRODUCES="bgr", DEFAULTS={}, run=lambda frames, row, params: frames(row),
           cut_file=lambda video, footage, params: None)
both = Tool(NAME="both", KIND="frame", EXPECTS="gray", PRODUCES="gray", INPUTS={"other": "gray"}, DEFAULTS={},
            run=lambda frames, row, params: frames(row))
TOOLS = {t.NAME: t for t in (cut, gray, add, same, both)}
FILE = {"cut": ("piece.mp4", "print")}


def test_a_served_node_and_all_after_it_are_keyed_as_the_document_opened_on_its_file():
    doc = D.from_tools([cut, gray, add])
    alone = plan(D.from_tools([gray, add]), TOOLS, base_key("print", "bgr"))
    served, live = plan(doc, TOOLS, "plate", FILE), plan(doc, TOOLS, "plate")
    assert served.entries["cut"].file == FILE["cut"] and served.entries["cut"].srcs == {"in": None} and served.entries["cut"].fed
    assert {n: served.entries[n].key for n in ("cut", "gray", "add")} == {"cut": alone.entries["video"].key, **{n: alone.entries[n].key for n in ("gray", "add")}}
    assert live.entries["cut"].file is None and live.entries["add"].key != served.entries["add"].key
    assert (served.entries["cut"].piece, served.entries["add"].piece, live.entries["add"].piece) == (None, "cut", "cut")
    doc.add_node("cut", id="inner")
    doc.connect("cut", "inner")
    inner = {"inner": ("inner.mp4", "inner print")}     # a cut of a served file is served; of a run it is not
    assert plan(doc, TOOLS, "plate", {**FILE, **inner}).entries["inner"].key == base_key("inner print", "bgr")
    assert plan(doc, TOOLS, "plate", inner).entries["inner"].file is None
    between = D.from_tools([same, cut, gray])       # the file is of the video, not of what a node between hands the cut
    between.nodes[1].tool, between.nodes[1].id = "pass", "pass"
    between.wires = [D.Wire("video", "pass"), D.Wire("pass", "cut"), D.Wire("cut", "gray")]
    through = Tool(**{**vars(cut), "NAME": "pass", "cut_file": None})
    assert plan(between, {**TOOLS, "pass": through}, "plate", FILE).entries["cut"].file is None


def test_a_node_whose_inputs_are_of_two_pieces_of_the_plate_is_not_fed_and_says_which():
    doc = D.from_tools([cut, gray])
    doc.add_node("gray", id="whole")
    doc.connect("video", "whole")
    doc.add_node("both")
    doc.connect("gray", "both")
    doc.connect("whole", "both", "other")
    doc.add_node("add")
    doc.connect("both", "add")
    for files in (None, FILE):       # refused cut or uncut: what a node may read never follows whether a file is there
        e = plan(doc, TOOLS, "plate", files).entries
        assert e["both"].standing == "reads across a cut: in is of cut, other of the plate" and not e["both"].fed
        assert not e["add"].fed and e["add"].standing == "in waits on both" and e["gray"].fed and e["whole"].fed


def test_a_graph_reads_a_served_nodes_rows_from_its_file_and_from_its_run_while_held_off(tmp_path):
    plate, piece = clip(tmp_path / "plate.avi"), clip(tmp_path / "piece.avi", h=24, w=32)
    asked = []
    cuts = Tool(**{**vars(cut), "cut_file": lambda video, footage, params: asked.append(video) or (piece, footage_print(piece))})
    doc = D.from_tools([cuts, gray], plate)
    doc.add_node("cut", id="inner")
    doc.connect("cut", "inner")
    g = Graph(doc, Decoder(plate), {"cut": cuts, "gray": gray})
    try:
        assert sorted(asked) == sorted([plate, piece])      # the cut below a served one is asked of the served file
        assert g.compute("cut", 2).shape == (24, 32, 3) and g.compute("gray", 2).shape == (24, 32)
        assert (g.footage("gray"), g.footage("cut")) == (piece, plate) and g.readers.open_on([piece])
        assert g.key("cut") == base_key(footage_print(piece), "bgr") != g.key("video")
        g.hold_off("cut", True)
        g.sync()
        assert g.compute("cut", 2).shape == (48, 64, 3) and g.footage("gray") == plate and g.entry("cut").file is None
    finally:
        g.close()
        g.decoder.close()


def test_region_answers_the_chosen_shapes_clip_while_the_record_is_of_this_footage_and_the_rect_the_shape_has(tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"plate")
    folder = tmp_path / "v-crops"
    folder.mkdir()
    (folder / "nest.mp4").write_bytes(b"nest")
    params = {**region.DEFAULTS, "plate": [48, 64], "choice": "nest",
              "shapes": [{"name": "nest", "polygon": [[10, 10], [30, 10], [30, 20], [10, 20]]}, {"name": "dish", "circle": [40, 30, 8]}]}
    (y0, y1, x0, x1), print_ = dict(region.crops(params))["nest"], footage_print(video)

    def record(**change):
        said = {"video": "v.mp4", "footage": print_, "plate": [48, 64],
                "crops": [{"name": "nest", "file": "nest.mp4", "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}], **change}
        (folder / "crops.json").write_text(json.dumps({k: v for k, v in said.items() if v is not None}), encoding="utf-8")
        os.utime(folder / "crops.json", ns=(record.at, record.at))      # a stamp of its own a write, whatever the clock's grain
        record.at += 10 ** 9
        return region.cut_file(str(video), print_, params)
    record.at = 10 ** 18

    assert record() == (str(folder / "nest.mp4"), footage_print(folder / "nest.mp4"))
    assert record(footage=None) is not None                             # a record that names the video and holds no print of it
    assert record(footage="another") is None and record(video="w.mp4") is None and record(plate=[24, 32]) is None
    assert record() is not None and region.cut_file(str(video), print_, {**params, "choice": ""}) is None
    assert region.cut_file(str(video), print_, {**params, "choice": "dish"}) is None       # a shape the cut did not write
    moved = [{"name": "nest", "polygon": [[12, 10], [32, 10], [32, 20], [12, 20]]}]
    assert region.cut_file(str(video), print_, {**params, "shapes": moved}) is None
    (folder / "nest.mp4").unlink()
    assert region.cut_file(str(video), print_, params) is None
